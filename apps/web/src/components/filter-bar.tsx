"use client";

import { Filter, Search } from "lucide-react";
import { usePathname, useRouter } from "next/navigation";
import type { FormEvent } from "react";

import { appendFilters, type FilterValues } from "@/lib/filters";

export function FilterBar({ filters }:{ filters:FilterValues }) {
  const pathname = usePathname();
  const router = useRouter();

  function submit(event:FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const data = new FormData(event.currentTarget);
    const values:FilterValues = {
      q:String(data.get("q") ?? "").trim(),
      market:String(data.get("market") ?? ""),
      importance:String(data.get("importance") ?? ""),
      status:String(data.get("status") ?? ""),
    };
    const query = appendFilters(new URLSearchParams(), values).toString();
    router.push(query ? `${pathname}?${query}` : pathname);
  }

  return (
    <form className="filter-bar" onSubmit={submit}>
      <label className="filter-search"><Search size={15} /><input name="q" defaultValue={filters.q} placeholder="搜索标题、机构、代码或备注" /></label>
      <label><span>市场</span><select name="market" defaultValue={filters.market}><option value="">全部市场</option><option>US</option><option>JP</option><option>KR</option><option>CN</option><option>TW</option><option>HK</option></select></label>
      <label><span>重要性</span><select name="importance" defaultValue={filters.importance}><option value="">全部级别</option><option value="critical">关键</option><option value="high">高</option><option value="medium">中</option></select></label>
      <label><span>状态</span><select name="status" defaultValue={filters.status}><option value="">全部状态</option><option value="confirmed">已确认</option><option value="expected">预计</option><option value="tba">时间待定</option><option value="rescheduled">已改期</option><option value="cancelled">已取消</option><option value="completed">已完成</option></select></label>
      <button type="submit"><Filter size={14} />筛选</button>
    </form>
  );
}
