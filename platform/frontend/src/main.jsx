import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import App from './App';
import './index.css';

// Create QueryClient instance
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5000,        // Data considered fresh for 5 seconds
      gcTime: 10 * 60 * 1000, // Clean up cache after 10 minutes
      refetchOnWindowFocus: false, // Don't auto-refresh on window focus
      retry: 1,               // Retry once on failure
    },
  },
});

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <App />
    </QueryClientProvider>
  </React.StrictMode>
);
