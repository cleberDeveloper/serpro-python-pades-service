module.exports = {
  apps: [
    {
      name: "serpro-python-pades-service",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 3333",
      cwd: "/opt/serpro-python-pades-service",
      interpreter: "none",
      instances: 1,
      exec_mode: "fork",
      autorestart: true,
      watch: false,
      max_memory_restart: "500M",
      error_file: "./logs/error.log",
      out_file: "./logs/out.log",
      log_file: "./logs/combined.log",
      time: true
    }
  ]
};
