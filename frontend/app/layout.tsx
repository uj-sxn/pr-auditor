import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "Agentic PR Auditor",
  description: "Mission Control dashboard for multi-agent PR governance",
  icons: {
    icon: "/icon.svg"
  }
};

export default function RootLayout({
  children
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
