"""
Simple test client that imports local tools from fastmcp_server.py and runs them directly.

Usage:
  1) Activate your venv and install dependencies: pip install fastmcp yt-dlp
  2) Edit SAMPLE_URL below to a short YouTube video URL you own or a public short video.
  3) Run: python mcp_client_test.py

This script does NOT speak the MCP network protocol; it simply imports the functions directly
to test the background-task and state management logic locally.
"""
import asyncio
import time
from fastmcp_server import download_video, get_download_status, JOBS

# Replace this with any short YouTube video URL for testing
SAMPLE_URL = 'https://www.youtube.com/watch?v=2Vv-BfVoq4g'  # edit to a short video


async def main():
    print('Starting local test: download_video')
    res = await download_video(SAMPLE_URL, download_path='./downloads_test')
    job_id = res['job_id']
    print('Job created:', job_id)

    # Poll the job status until it finishes or errors
    while True:
        status = await get_download_status(job_id)
        print('Status:', status['status'], 'Progress:', status['progress'].get('percent'))
        if status['status'] in ('completed', 'error', 'cancelled'):
            print('Final status:', status)
            break
        await asyncio.sleep(2)


if __name__ == '__main__':
    asyncio.run(main())
