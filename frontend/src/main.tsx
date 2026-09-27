import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import AccessGate from "./components/AccessGate";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <BrowserRouter>
      <AccessGate>
        <App />
      </AccessGate>
    </BrowserRouter>
  </React.StrictMode>,
);
