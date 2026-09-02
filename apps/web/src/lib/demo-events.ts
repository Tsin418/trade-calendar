export type CalendarEvent = {
  id: string;
  title: string;
  originalTitle: string;
  institution: string;
  country: string;
  market: string;
  category: string;
  importance: "critical" | "high" | "medium" | "low";
  status: "confirmed" | "tba" | "expected" | "rescheduled" | "cancelled";
  precision: "minute" | "date";
  start?: string;
  localDate?: string;
  originalTime?: string;
  source: string;
};

export const demoEvents: CalendarEvent[] = [
  { id:"boj-base", title:"日本央行货币基础", originalTitle:"Monetary Base", institution:"Bank of Japan", country:"JP", market:"JP", category:"宏观数据", importance:"medium", status:"confirmed", precision:"minute", start:"2026-09-02T14:00:00+08:00", originalTime:"15:00 JST", source:"Bank of Japan" },
  { id:"us-productivity", title:"美国非农生产力修正值", originalTitle:"Productivity and Costs, Revised", institution:"U.S. Bureau of Labor Statistics", country:"US", market:"US", category:"宏观数据", importance:"high", status:"confirmed", precision:"minute", start:"2026-09-02T20:30:00+08:00", originalTime:"08:30 ET", source:"BLS" },
  { id:"factory-orders", title:"美国工厂订单", originalTitle:"Manufacturers' Shipments, Inventories and Orders", institution:"U.S. Census Bureau", country:"US", market:"US", category:"宏观数据", importance:"medium", status:"confirmed", precision:"minute", start:"2026-09-02T22:00:00+08:00", originalTime:"10:00 ET", source:"U.S. Census Bureau" },
  { id:"jobless", title:"美国初请失业金人数", originalTitle:"Unemployment Insurance Weekly Claims", institution:"U.S. Department of Labor", country:"US", market:"US", category:"就业", importance:"high", status:"confirmed", precision:"minute", start:"2026-09-03T20:30:00+08:00", originalTime:"08:30 ET", source:"U.S. Department of Labor" },
  { id:"hk-retail", title:"香港零售销售", originalTitle:"Retail Sales", institution:"Census and Statistics Department", country:"HK", market:"HK", category:"宏观数据", importance:"high", status:"confirmed", precision:"minute", start:"2026-09-03T16:30:00+08:00", originalTime:"16:30 HKT", source:"C&SD" },
  { id:"korea-cpi", title:"韩国消费者价格指数", originalTitle:"Consumer Price Index", institution:"Statistics Korea", country:"KR", market:"KR", category:"通胀", importance:"high", status:"rescheduled", precision:"minute", start:"2026-09-04T07:00:00+08:00", originalTime:"08:00 KST", source:"Statistics Korea" },
  { id:"nfp", title:"美国就业报告", originalTitle:"The Employment Situation", institution:"U.S. Bureau of Labor Statistics", country:"US", market:"GLOBAL", category:"就业", importance:"critical", status:"confirmed", precision:"minute", start:"2026-09-04T20:30:00+08:00", originalTime:"08:30 ET", source:"BLS" },
  { id:"tsmc-date", title:"台积电月度营收", originalTitle:"Monthly Revenue", institution:"TSMC", country:"TW", market:"TW", category:"公司事件", importance:"high", status:"tba", precision:"date", localDate:"2026-09-10", source:"TSMC IR" },
  { id:"fomc", title:"FOMC 利率决议", originalTitle:"Federal Open Market Committee Meeting", institution:"Federal Reserve", country:"US", market:"GLOBAL", category:"货币政策", importance:"critical", status:"confirmed", precision:"minute", start:"2026-09-16T02:00:00+08:00", originalTime:"14:00 ET", source:"Federal Reserve" },
  { id:"boj", title:"日本央行利率决议", originalTitle:"Monetary Policy Meeting", institution:"Bank of Japan", country:"JP", market:"JP", category:"货币政策", importance:"critical", status:"tba", precision:"date", localDate:"2026-09-18", source:"Bank of Japan" },
  { id:"bok", title:"韩国央行利率决议", originalTitle:"Monetary Policy Board Meeting", institution:"Bank of Korea", country:"KR", market:"KR", category:"货币政策", importance:"critical", status:"confirmed", precision:"minute", start:"2026-10-22T09:00:00+08:00", originalTime:"10:00 KST", source:"Bank of Korea" },
];

export const labels = {
  importance: { critical:"关键", high:"高", medium:"中", low:"低" },
  status: { confirmed:"已确认", tba:"时间待定", expected:"预计", rescheduled:"已改期", cancelled:"已取消" },
};

export function eventDate(event: CalendarEvent): string {
  return event.start?.slice(0, 10) ?? event.localDate ?? "";
}

