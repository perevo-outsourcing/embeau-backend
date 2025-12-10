#!/bin/bash
# EMBEAU API Server 실행 스크립트
# PM2와 함께 사용

# 프로젝트 루트로 이동 (.env 파일 위치)
cd /home/ali/storage6/sxngt/embeau-backend

# PYTHONPATH 설정 (src 디렉토리 포함)
export PYTHONPATH="/home/ali/storage6/sxngt/embeau-backend/src:$PYTHONPATH"

# Python 출력 버퍼링 비활성화 (실시간 로깅)
export PYTHONUNBUFFERED=1

# 가상환경의 Python으로 uvicorn 실행
# pydantic-settings가 .env 파일을 자동으로 읽음
exec /home/ali/storage6/sxngt/embeau-backend/.venv/bin/python -m uvicorn \
    embeau_api.main:app \
    --host 0.0.0.0 \
    --port 8888
