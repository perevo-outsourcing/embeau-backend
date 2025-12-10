module.exports = {
  apps: [
    {
      name: "embeau-api",

      // 쉘 스크립트를 통한 실행
      script: "./scripts/run_server.sh",
      interpreter: "/bin/bash",

      // 작업 디렉토리
      cwd: "/home/ali/storage6/sxngt/embeau-backend",

      // 무중단 배포를 위한 설정
      instances: 1,                    // 단일 인스턴스
      exec_mode: "fork",               // fork 모드
      kill_timeout: 5000,              // graceful shutdown 대기 시간 (ms)

      // 자동 재시작 설정
      autorestart: true,
      max_restarts: 10,
      min_uptime: "10s",
      restart_delay: 1000,

      // 로깅 설정
      log_date_format: "YYYY-MM-DD HH:mm:ss Z",
      error_file: "./logs/error.log",
      out_file: "./logs/out.log",
      combine_logs: true,
      merge_logs: true,

      // 환경 변수 (개발용)
      env: {
        NODE_ENV: "development",
        PYTHONUNBUFFERED: "1",         // Python 출력 버퍼링 비활성화 (실시간 로그)
        PYTHONPATH: "/home/ali/storage6/sxngt/embeau-backend/src",
      },

      // 환경 변수 (운영용) - pm2 start ecosystem.config.js --env production
      env_production: {
        NODE_ENV: "production",
        PYTHONUNBUFFERED: "1",
        PYTHONPATH: "/home/ali/storage6/sxngt/embeau-backend/src",
      },

      // 파일 변경 감지 (개발 시에만 true로 설정)
      watch: false,
      ignore_watch: ["logs", "*.log", "__pycache__", ".git", ".venv", "node_modules"],
    },
  ],
};
