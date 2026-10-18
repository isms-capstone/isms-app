import { notFound } from "next/navigation";
import { CaseDetail } from "@/components/cases/case-detail";
export default async function Page({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  if (!/^\d+$/.test(id)) notFound();
  return <CaseDetail id={Number(id)} />;
}
