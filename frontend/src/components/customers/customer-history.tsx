"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { AppShell } from "@/components/layout/app-shell";
import { useSession } from "@/components/providers/session-provider";
import { all, api } from "@/lib/api";
import {
  statusNames,
  type Organization,
  type Product,
  type Ticket,
} from "@/lib/types";

export function CustomerHistory({ id }: { id: number }) {
  const { session } = useSession();
  const [customer, setCustomer] = useState<Organization>();
  const [products, setProducts] = useState<Product[]>([]);
  const [rows, setRows] = useState<Ticket[]>();
  const [product, setProduct] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    Promise.all([
      api<Organization>(`/customers/organizations/${id}`, {
        signal: controller.signal,
      }),
      all<Product>("/products", controller.signal),
    ])
      .then(([organization, products]) => {
        setCustomer(organization);
        setProducts(products);
      })
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      });
    return () => controller.abort();
  }, [id, session]);

  useEffect(() => {
    if (!session) return;
    const controller = new AbortController();
    const query = new URLSearchParams({
      organization_id: String(id),
      published_only: "true",
    });
    if (product) query.set("product_id", product);
    if (status) query.set("ticket_status", status);
    all<Ticket>(`/tickets?${query}`, controller.signal)
      .then(setRows)
      .catch((error) => {
        if (!controller.signal.aborted) setError(error.message);
      });
    return () => controller.abort();
  }, [id, product, status, session]);

  return (
    <AppShell title="ประวัติเคสลูกค้า">
      <div className="page-heading">
        <div>
          <Link className="text-link" href="/customers">
            กลับไปที่ลูกค้า
          </Link>
          <h1>{customer?.name ?? "ประวัติเคสลูกค้า"}</h1>
        </div>
      </div>
      <section className="surface detail-card">
        <div className="detail-grid mb-4">
          <label>
            ผลิตภัณฑ์
            <select
              className="input block w-full"
              value={product}
              onChange={(e) => {
                setRows(undefined);
                setProduct(e.target.value);
              }}
            >
              <option value="">ทุกผลิตภัณฑ์</option>
              {products.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.name}
                </option>
              ))}
            </select>
          </label>
          <label>
            สถานะ
            <select
              className="input block w-full"
              value={status}
              onChange={(e) => {
                setRows(undefined);
                setStatus(e.target.value);
              }}
            >
              <option value="">ทุกสถานะ</option>
              {Object.entries(statusNames)
                .filter(([value]) => value !== "DRAFT")
                .map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
            </select>
          </label>
        </div>
        {error && <p role="alert">{error}</p>}
        {!rows && !error && <p role="status">กำลังโหลดประวัติเคส</p>}
        {rows?.length === 0 && <p>ไม่พบเคสตามตัวกรองที่เลือก</p>}
        {!!rows?.length && (
          <table className="customer-list">
            <thead>
              <tr>
                <th>เคส</th>
                <th>เวลาสร้าง</th>
                <th>สถานะ</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row) => (
                <tr key={row.id}>
                  <td>
                    <Link className="text-link" href={`/cases/${row.id}`}>
                      {row.ticket_no} · {row.subject}
                    </Link>
                  </td>
                  <td>{new Date(row.created_at).toLocaleString("th-TH")}</td>
                  <td>{statusNames[row.status] ?? row.status}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </AppShell>
  );
}
