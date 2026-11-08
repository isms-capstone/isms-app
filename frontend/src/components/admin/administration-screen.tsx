"use client";

import Link from "next/link";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { MasterDataCollection } from "./master-data-screen";
import {
  administrationCollections,
  administrationGroups,
} from "./administration-config";

export function AdministrationScreen({ section }: { section: string }) {
  const { session } = useSession();
  const group = administrationGroups.find((item) =>
    item.sections.includes(section),
  );
  const config = administrationCollections[section];

  return (
    <AppShell title={group?.title ?? "Administration"}>
      <div className="page-heading">
        <div>
          <h1>{group?.title ?? "Administration"}</h1>
          <p>{group?.description}</p>
        </div>
      </div>
      {session?.role === "Admin" && group && config ? (
        <>
          {group.sections.length > 1 && (
            <nav className="master-data-nav" aria-label={group.title}>
              {group.sections.map((key) => (
                <Link
                  href={`/administration/${key}`}
                  aria-current={key === section ? "page" : undefined}
                  key={key}
                >
                  {administrationCollections[key].title}
                </Link>
              ))}
            </nav>
          )}
          <MasterDataCollection
            key={section}
            section={section}
            config={config}
          />
        </>
      ) : (
        <p className="surface master-data-card">
          ไม่พบหน้า หรือบัญชีนี้ไม่มีสิทธิ์เข้าถึง
        </p>
      )}
    </AppShell>
  );
}
