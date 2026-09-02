import { Filter, Search } from "lucide-react";

export function FilterBar() {
  return (
    <form className="filter-bar" action="">
      <label className="filter-search"><Search size={15} /><input name="q" placeholder="搜索标题、机构、代码或备注" /></label>
      <label><span>市场</span><select name="market" defaultValue=""><option value="">全部市场</option><option>US</option><option>JP</option><option>KR</option><option>TW</option><option>HK</option></select></label>
      <label><span>重要性</span><select name="importance" defaultValue=""><option value="">全部级别</option><option value="critical">关键</option><option value="high">高</option><option value="medium">中</option></select></label>
      <label><span>状态</span><select name="status" defaultValue=""><option value="">全部状态</option><option value="confirmed">已确认</option><option value="tba">时间待定</option><option value="rescheduled">已改期</option></select></label>
      <button type="submit"><Filter size={14} />筛选</button>
    </form>
  );
}

