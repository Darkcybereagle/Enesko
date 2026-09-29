import "./globals.css";

export const metadata = {
  title: "ENESKO | Ikeja City Mall",
  description: "AI-powered mall discovery, indoor navigation and customer operations.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
