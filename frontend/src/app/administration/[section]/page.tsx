import { AdministrationScreen } from "@/components/admin/administration-screen";

export default async function Page({
  params,
}: {
  params: Promise<{ section: string }>;
}) {
  return <AdministrationScreen section={(await params).section} />;
}
