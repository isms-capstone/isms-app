import { notFound } from "next/navigation";
import { QueueScreen } from "@/components/cases/queue-screen";

/** Any product code from the catalogue works; new products need no deployment. */
export default async function Page({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  if (!/^[a-z0-9][a-z0-9_-]{0,49}$/.test(slug)) notFound();
  return <QueueScreen product={slug} />;
}
