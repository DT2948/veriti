import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Veriti Dashboard",
  description: "Live crisis verification dashboard for Dubai incidents.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
