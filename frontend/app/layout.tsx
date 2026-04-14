import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "TrustLens AI - Dataset Bias Detection & Trust Framework",
  description:
    "Upload datasets, detect bias before model training, compute fairness metrics, and generate explainable trust reports."
};

type RootLayoutProps = Readonly<{
  children: React.ReactNode;
}>;

export default function RootLayout({ children }: RootLayoutProps) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
