import type { Metadata } from "next";
import "./globals.css";
import { WorkspaceProvider } from "./workspace-context";
import { WorkspaceShell } from "./workspace-shell";

export const metadata: Metadata = {
  title: "Takshyra | Operations",
  description: "Local data reliability operations workbench",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body><WorkspaceProvider><WorkspaceShell>{children}</WorkspaceShell></WorkspaceProvider></body>
    </html>
  );
}
