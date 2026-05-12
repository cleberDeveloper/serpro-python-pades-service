module.exports = {
  apps: [
    {
      name: "serpro-python-pades-service",
      script: ".venv/bin/uvicorn",
      args: "app.main:app --host 0.0.0.0 --port 3333",
      cwd: "/opt/serpro-python-pades-service",
      interpreter: "none"
    }
  ]
};
