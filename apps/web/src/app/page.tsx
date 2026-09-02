import {
  Bell, CalendarDays, ChevronRight, FileClock, Globe2, RefreshCw, Search,
  ShieldCheck,
} from "lucide-react";
import { Sidebar } from "@/components/sidebar";
import { SourceHealthSummary } from "@/components/source-health";

const events = [
  { time: "14:00", origin: "15:00 JST", code: "JP", title: "日本央行货币基础", source: "Bank of Japan", level: "MEDIUM", passed: true },
  { time: "20:30", origin: "08:30 ET", code: "US", title: "美国非农生产力修正值", source: "U.S. Bureau of Labor Statistics", level: "HIGH" },
  { time: "22:00", origin: "10:00 ET", code: "US", title: "美国工厂订单", source: "U.S. Census Bureau", level: "MEDIUM" },
];

export default function Home() {
  return (
    <div className="shell">
      <Sidebar />

      <main>
        <header>
          <div><small>2026 年 9 月 2 日 · 星期三</small><h1>早上好，今天有 <span>3</span> 个事件</h1></div>
          <div className="actions">
            <button className="search"><Search size={17} />搜索事件 <kbd>⌘ K</kbd></button>
            <button className="bell" aria-label="通知"><Bell size={18} /><i /></button>
            <button className="sync"><RefreshCw size={16} />立即同步</button>
          </div>
        </header>

        <div className="context"><span><Globe2 size={15} />上海时间 · UTC+8 <ChevronRight size={14} /></span><p>上次同步：10:46 · 所有核心来源均为最新</p></div>

        <section className="hero">
          <article className="next-card">
            <div className="next-label"><span><i />下一个关键事件</span><b>CRITICAL</b></div>
            <div className="next-body">
              <div><small><b>US</b> 美国 · 货币政策</small><h2>FOMC 利率决议</h2><p>Federal Open Market Committee Meeting</p></div>
              <div className="countdown"><span><b>13</b><small>天</small></span><i>:</i><span><b>07</b><small>小时</small></span><i>:</i><span><b>14</b><small>分钟</small></span></div>
            </div>
            <footer><span><CalendarDays size={15} />9 月 16 日 02:00 · 14:00 ET</span><span><ShieldCheck size={15} />Federal Reserve · 已确认</span></footer>
          </article>
          <div className="metrics">
            <article><span>今日事件 <CalendarDays size={18} /></span><strong>3</strong><p><b>2</b> 个尚未发生</p></article>
            <article><span>新增 / 变更 <FileClock size={18} /></span><strong>3</strong><p><b className="orange">1</b> 个高影响变更</p></article>
          </div>
        </section>

        <section className="content">
          <article className="panel timeline-panel">
            <div className="panel-head"><div><h2>今日时间线</h2><p>按上海时间排序</p></div><a href="#">查看今天 <ChevronRight size={15} /></a></div>
            <div className="timeline">
              {events.map((event) => (
                <div className={`event ${event.passed ? "passed" : ""}`} key={event.title}>
                  <div className="time"><b>{event.time}</b><small>{event.origin}</small></div>
                  <i className={event.level === "HIGH" ? "high-dot" : ""} />
                  <div className="event-copy"><small>{event.code} · {event.source}</small><h3>{event.title}</h3></div>
                  <div className="event-state"><b className={event.level === "HIGH" ? "high" : "medium"}>{event.level}</b><small>已确认</small></div>
                  <ChevronRight size={17} />
                </div>
              ))}
            </div>
          </article>

          <article className="panel week-panel">
            <div className="panel-head"><div><h2>本周重点</h2><p>3 个高影响事件</p></div><a href="#">查看本周 <ChevronRight size={15} /></a></div>
            <div className="week-list">
              <WeekItem day="03" weekday="周四" title="美国初请失业金人数" time="20:30" />
              <WeekItem day="04" weekday="周五" title="韩国消费者价格指数" time="07:00" />
              <WeekItem day="04" weekday="周五" title="美国就业报告" time="20:30" critical />
            </div>
          </article>
        </section>

        <section className="bottom">
          <article className="panel changes">
            <div className="panel-head"><div><h2>最近变更</h2><p>过去 24 小时</p></div><a href="#">查看全部 <ChevronRight size={15} /></a></div>
            <div className="change"><span><RefreshCw size={15} /></span><div><h3>韩国 GDP 终值已改期</h3><p>9 月 3 日 07:00 → 9 月 4 日 07:00</p></div><time>28 分钟前</time></div>
            <div className="change"><span className="added">+</span><div><h3>新增：香港零售销售</h3><p>High · 9 月 3 日 16:30</p></div><time>1 小时前</time></div>
          </article>
          <article className="panel sources">
            <div className="panel-head"><div><h2>来源健康</h2><p>核心数据源实时状态</p></div><a href="/sources">详情 <ChevronRight size={15} /></a></div>
            <SourceHealthSummary />
          </article>
        </section>
      </main>
    </div>
  );
}

function WeekItem({ day, weekday, title, time, critical = false }: { day: string; weekday: string; title: string; time: string; critical?: boolean }) {
  return <div className="week-item"><div className="date"><b>{day}</b><small>{weekday}</small></div><div><h3>{title}</h3><p>{time} · 上海时间</p></div><i className={critical ? "critical" : ""} /></div>;
}
