import type { Metadata } from "next";
import { ReportSite } from "./ReportSite";

export const metadata: Metadata = {
  title: "SummerTestModel — 39 local models on one laptop",
  description:
    "A bilingual, evidence-first report for SummerTestModel Benchmark 1.0-rc1: 39 local Ollama models and 1,938 task records.",
  openGraph: {
    title: "SummerTestModel Benchmark 1.0-rc1",
    description: "39 local models. 1,938 task records. One practical Windows laptop.",
    images: ["/og.png"],
  },
};

export default function Home() {
  return <ReportSite />;
}
