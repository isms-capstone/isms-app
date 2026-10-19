import { notFound } from "next/navigation";
import { QueueScreen } from "@/components/cases/queue-screen";
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const name: Record<string, string> = {
    examplus: "ExamPlus",
    geta: "GetA",
    logbook: "Logbook",
  };
  if (!name[slug]) notFound();
  return <QueueScreen product={name[slug]} />;
}
