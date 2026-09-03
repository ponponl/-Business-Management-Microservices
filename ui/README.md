# React + Vite

## Run With Kubernetes

Run a fixed port-forward for the Minikube gateway in one terminal and keep it open:

```powershell
kubectl port-forward service/api-gateway -n business-management 8090:80
```

In a second terminal, run the UI with Kubernetes mode:

```powershell
npm run dev:kubernetes
```

The Kubernetes UI mode uses `http://localhost:8090`. This avoids the Docker Compose gateway port (`8080`) and the local service ports (`8081`-`8087`).

When `VITE_API_BASE_URL` is set, requests that currently use the local Compose ports are routed through the Kubernetes API Gateway. Without it, the existing Docker Compose URLs remain unchanged.

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.
