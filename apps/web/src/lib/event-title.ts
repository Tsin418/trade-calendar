import type { ApiEvent } from "./api";

export function eventTitle(event:ApiEvent):string {
  return [event.display_title, event.title_original, event.title_zh]
    .find((text) => text?.trim() && !needsTranslation(text))?.trim() || "标题翻译中";
}

export function needsTranslation(text:string|null|undefined):boolean {
  return Boolean(text && /[\u1100-\u11ff\u3040-\u30ff\u3130-\u318f\ua960-\ua97f\uac00-\ud7ff\uff66-\uff9f]/.test(text));
}

export function displayText(text:string|null|undefined, placeholder = "翻译中"):string {
  return text?.trim() && !needsTranslation(text) ? text : placeholder;
}

export function eventInstitution(event:ApiEvent):string {
  return displayText(event.display_institution || event.institution, "机构名称翻译中");
}

export function eventOriginalTime(event:ApiEvent):string|undefined {
  const text = event.display_original_time_text ?? event.original_time_text;
  return text ? displayText(text) : undefined;
}
