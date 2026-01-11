import { createRoot } from "react-dom/client";
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';
import App from "./App.tsx";
import "./index.css";

// React Query Client mit Default-Konfiguration
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,           // Daten gelten 5s als "fresh"
      gcTime: 10 * 60 * 1000,    // Cache für 10 Minuten
      refetchOnWindowFocus: true,
      retry: 1,
    },
  },
});

createRoot(document.getElementById("root")!).render(
  <QueryClientProvider client={queryClient}>
    <App />
    <ReactQueryDevtools initialIsOpen={false} />
  </QueryClientProvider>
);