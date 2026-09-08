import type { Metadata } from "next";
import "@/app/home/style.css";
import Navbar from "@/app/components/landing/Navbar";
import Footer from "@/app/components/landing/Footer";
import PrivacyPolicy from "@/components/PrivacyPolicy";

export const metadata: Metadata = {
  title: "GSearchAI Privacy Policy",
  description:
    "GSearchAI Privacy Policy explains how we collect, use, process, store, and protect user and Google Drive data when using the GSearchAI platform and Google Drive connector.",
  alternates: {
    canonical: "https://gsearchai.com/privacy-policy",
  },
  openGraph: {
    title: "GSearchAI Privacy Policy",
    description:
      "GSearchAI Privacy Policy explains how we collect, use, process, store, and protect user and Google Drive data when using the GSearchAI platform and Google Drive connector.",
    url: "https://gsearchai.com/privacy-policy",
    siteName: "GSearchAI",
    type: "website",
  },
};

export default function PrivacyPolicyPage() {
  return (
    <main className="min-h-screen bg-white">
      <Navbar />
      <PrivacyPolicy />
      <Footer />
    </main>
  );
}
