import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Takshyra | Operations",
  description: "Local data reliability operations workbench",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
