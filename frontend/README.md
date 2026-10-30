# VM Controller — Modern React SPA Frontend

A modern, high-performance infrastructure dashboard for the PS-023 Cloud Hypervisor VM Controller.

## Architecture

- **Framework**: React 19 + TypeScript + Vite
- **Icons**: [Lucide React](https://lucide.dev/)
- **Visuals**: Three.js & GSAP for real-time cluster visualization and topology inspection
- **Charts**: Recharts for live node memory, CPU, and cluster headroom metrics
- **Terminal**: Embedded `@xterm/xterm` with `@xterm/addon-fit` communicating over WebSocket SSH sessions directly to microVMs

## Views Included

1. **Overview**: Cluster health, node capacity, active virtual machines, and real-time resource utilization.
2. **Nodes**: Live node telemetry, schedulable memory vs total, CPU allocation, heartbeat status.
3. **VMs**: Full VM lifecycle management (create, start, stop, terminal, delete).
4. **Placement Decisions**: Real-time auditing of controller scheduling decisions and node eligibility.
5. **Terminals**: Integrated browser terminal tabs connecting directly to guest instances via WebSocket.
6. **Images**: Available microVM base image profiles and status.
7. **System Events**: Real-time structured controller audit log.

## Getting Started

### Development
```bash
cd frontend
npm install
npm run dev
```

### Production Build
```bash
cd frontend
npm run build
```
The compiled single-page application is emitted into `src/controller/dashboard/` and served automatically by the FastAPI controller at `http://127.0.0.1:8000/dashboard/`.

### Automated UI Tests
```bash
cd frontend
npm test
```
