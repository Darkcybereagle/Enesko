import "./globals.css";

export const metadata = {
  title: "ENESKO Tenant | Mall Operations Workspace",
  description: "Tenant operations workspace for ENESKO intelligent mall operations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
