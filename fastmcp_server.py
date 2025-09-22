# pip install fastmcp yt-dlp
"""
MCP server using fastmcp that manages YouTube downloads via yt-dlp.

Dependencies:
    pip install fastmcp yt-dlp

This script exposes 6 async tools:
 - download_video(url, download_path)
 - download_playlist(url, download_path)
 - get_download_status(job_id)
 - cancel_download(job_id)
 - list_downloads()
 - get_video_metadata(url)

Run as a standalone MCP provider:
    python fastmcp_server.py

The server keeps an in-memory dict `JOBS` mapping job_id -> job info.
Each job contains: job_id, url, status, progress, error_message, output_path, cancel_flag, task

Notes about cancellation: yt-dlp doesn't provide a direct async cancel API. We run yt-dlp in the current event loop but in a background asyncio Task and use a cancel flag. The progress hook checks the flag and raises an exception to abort if requested. This gives a cooperative cancellation.
"""
import asyncio
import uuid
import os
import traceback
from typing import Dict, Any, Optional

import yt_dlp
from fastmcp import MCPServer, Tool

# Global job state
JOBS: Dict[str, Dict[str, Any]] = {}


def _make_job_entry(url: str, download_path: str) -> Dict[str, Any]:
    return {
        "job_id": str(uuid.uuid4()),
        "url": url,
        "status": "pending",
        "progress": {"percent": 0.0, "downloaded_bytes": 0, "total_bytes": None},
        "error_message": None,
        "output_path": None,
        # internal control flags / objects
        "cancel_requested": False,
        "task": None,  # will hold the asyncio.Task
    }


async def _run_yt_dlp_job(job: Dict[str, Any], ydl_opts: Dict[str, Any]):
    """Run yt-dlp synchronously via its API but non-blocking in an asyncio Task.

    The function uses a progress_hook to update job['progress'] and to check for cancellation.
    """

    def progress_hook(d):
        # This hook is called in the thread that runs yt-dlp internals; in this context it's the same thread
        try:
            status = d.get('status')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate')
                downloaded = d.get('downloaded_bytes', 0)
                percent = d.get('downloaded_bytes') / total * 100 if total else 0.0
                job['progress'].update({
                    'percent': round(percent, 2),
                    'downloaded_bytes': downloaded,
                    'total_bytes': total,
                })
            elif status == 'finished':
                job['progress']['percent'] = 100.0
        except Exception:
            # Safe-guard: never let progress hook crash the downloader
            pass

        # Cooperative cancellation: if cancel requested, raise an error to stop yt-dlp
        if job.get('cancel_requested'):
            raise yt_dlp.utils.DownloadError('Cancelled by user')

    ydl_opts = dict(ydl_opts)
    hooks = ydl_opts.get('progress_hooks', [])
    hooks.append(progress_hook)
    ydl_opts['progress_hooks'] = hooks

    # Ensure download path exists
    outtmpl = ydl_opts.get('outtmpl')
    if outtmpl:
        parent = os.path.dirname(outtmpl)
        if parent:
            os.makedirs(parent, exist_ok=True)

    loop = asyncio.get_event_loop()

    # Run yt-dlp in a thread to avoid blocking the event loop
    try:
        job['status'] = 'downloading'

        def blocking():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.download([job['url']])
                return res

        await loop.run_in_executor(None, blocking)

        # If finished without exception, update job
        job['status'] = 'completed'
        # try to set the output path if using outtmpl
        if outtmpl:
            # yt-dlp may write multiple files for playlists; store the template path
            job['output_path'] = os.path.abspath(outtmpl)
    except Exception as e:
        # If cancelled, mark as cancelled
        if job.get('cancel_requested'):
            job['status'] = 'cancelled'
            job['error_message'] = 'Cancelled by user'
        else:
            job['status'] = 'error'
            job['error_message'] = ''.join(traceback.format_exception_only(type(e), e)).strip()


async def download_video(url: str, download_path: str = './downloads') -> Dict[str, Any]:
    """Start downloading a single video. Returns the job_id."""
    job = _make_job_entry(url, download_path)
    job_id = job['job_id']
    JOBS[job_id] = job

    # Configure yt-dlp options for single video
    os.makedirs(download_path, exist_ok=True)
    outtmpl = os.path.join(download_path, '%(title)s - %(id)s.%(ext)s')
    ydl_opts = {
        'outtmpl': outtmpl,
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    # Schedule the background task
    task = asyncio.create_task(_run_yt_dlp_job(job, ydl_opts))
    job['task'] = task

    # Return job id
    return {"job_id": job_id}


async def download_playlist(url: str, download_path: str = './downloads') -> Dict[str, Any]:
    """Start downloading a playlist. Returns the job_id."""
    job = _make_job_entry(url, download_path)
    job_id = job['job_id']
    JOBS[job_id] = job

    os.makedirs(download_path, exist_ok=True)
    outtmpl = os.path.join(download_path, '%(playlist)s', '%(playlist_index)s - %(title)s - %(id)s.%(ext)s')
    ydl_opts = {
        'outtmpl': outtmpl,
        'yesplaylist': True,
        'quiet': True,
        'no_warnings': True,
    }

    task = asyncio.create_task(_run_yt_dlp_job(job, ydl_opts))
    job['task'] = task

    return {"job_id": job_id}


async def get_download_status(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job_id not found", "job_id": job_id}
    # Return a clean copy (avoid returning the task object)
    copy = {k: v for k, v in job.items() if k != 'task'}
    return copy


async def cancel_download(job_id: str) -> Dict[str, Any]:
    job = JOBS.get(job_id)
    if not job:
        return {"error": "job_id not found", "job_id": job_id}

    if job['status'] in ('completed', 'error', 'cancelled'):
        return {"status": "cannot_cancel", "reason": f"job already {job['status']}", "job_id": job_id}

    # Set cancel flag. The progress_hook checks this flag and will raise to abort.
    job['cancel_requested'] = True

    # Also attempt to cancel the asyncio.Task if it's still pending
    task: Optional[asyncio.Task] = job.get('task')
    if task and not task.done():
        try:
            task.cancel()
        except Exception:
            pass

    job['status'] = 'cancel_requested'
    return {"status": "cancellation_requested", "job_id": job_id}


async def list_downloads() -> Dict[str, Any]:
    # Return brief info for all jobs
    return [
        {k: v for k, v in job.items() if k not in ('task',)} for job in JOBS.values()
    ]


async def get_video_metadata(url: str) -> Dict[str, Any]:
    """Extract metadata using yt-dlp without downloading."""
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        # 'extract_flat': True,  # for playlists we might want a flat list
    }

    loop = asyncio.get_event_loop()

    def blocking_extract():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            return info

    info = await loop.run_in_executor(None, blocking_extract)
    return info


def _create_server():
    server = MCPServer()

    # Register tools
    server.register_tool(Tool('download_video', download_video))
    server.register_tool(Tool('download_playlist', download_playlist))
    server.register_tool(Tool('get_download_status', get_download_status))
    server.register_tool(Tool('cancel_download', cancel_download))
    server.register_tool(Tool('list_downloads', list_downloads))
    server.register_tool(Tool('get_video_metadata', get_video_metadata))

    return server


if __name__ == '__main__':
    # Run the MCP server
    srv = _create_server()
    print('Starting fastmcp server with YouTube downloader tools...')
    # Default host/port can be configured via args or env in real deployments
    srv.run()
