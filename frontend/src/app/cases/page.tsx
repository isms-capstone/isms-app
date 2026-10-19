import { QueueScreen } from "@/components/cases/queue-screen";
export default async function Page({
  searchParams,
}: {
  searchParams: Promise<{ q?: string }>;
}) {
  const { q } = await searchParams;
  return <QueueScreen key={q || ""} view="all" initialQuery={q} />;
}
