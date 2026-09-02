import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { App } from './App';
import { i18nReady } from './i18n';
import './index.css';

const container = document.getElementById('root');
if (!container) {
  throw new Error('#root missing from index.html');
}

void i18nReady.then(() => {
  createRoot(container).render(
    <StrictMode>
      <App />
    </StrictMode>,
  );
});
