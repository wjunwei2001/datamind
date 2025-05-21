const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

// Path to backend directory
const backendPath = path.resolve(__dirname, '../../backend');

// Check if .env.local file exists, if not create it
const envPath = path.resolve(__dirname, '.env.local');
if (!fs.existsSync(envPath)) {
  console.log('Creating .env.local file with default settings...');
  fs.writeFileSync(
    envPath,
    'NEXT_PUBLIC_API_URL=http://localhost:8000\n'
  );
}

// Function to spawn a process
function spawnProcess(command, args, cwd, name) {
  const proc = spawn(command, args, {
    cwd,
    shell: true,
    stdio: 'pipe', // Capture stdout and stderr
  });

  // Prefix logs with name
  proc.stdout.on('data', (data) => {
    console.log(`[${name}] ${data.toString().trim()}`);
  });

  proc.stderr.on('data', (data) => {
    console.error(`[${name}] ${data.toString().trim()}`);
  });

  proc.on('error', (err) => {
    console.error(`[${name}] Failed to start: ${err.message}`);
  });

  proc.on('exit', (code) => {
    console.log(`[${name}] Process exited with code ${code}`);
  });

  return proc;
}

// Start backend
console.log('Starting backend server...');
const backend = spawnProcess('python', ['main.py'], backendPath, 'Backend');

// Start frontend
console.log('Starting frontend dev server...');
const frontend = spawnProcess('npm', ['run', 'dev'], __dirname, 'Frontend');

// Handle process termination
process.on('SIGINT', () => {
  console.log('\nShutting down development servers...');
  backend.kill();
  frontend.kill();
  process.exit(0);
});

process.on('SIGTERM', () => {
  console.log('\nShutting down development servers...');
  backend.kill();
  frontend.kill();
  process.exit(0);
}); 