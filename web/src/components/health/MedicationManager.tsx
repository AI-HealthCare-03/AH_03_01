"use client";

import { useEffect, useState } from "react";
import { type QueryClient, useQueryClient } from "@tanstack/react-query";
import { upsertHealthProfile } from "@/lib/api/health";
import { HEALTH_PROFILE_KEY } from "@/hooks/queries/useHealthProfile";
import { medSnapshotKey } from "@/lib/notifKeys";

/* ─────────────────────────────────────────────────────
   복약 관리 컴포넌트 — localStorage 기반
   키: "medication-list"
───────────────────────────────────────────────────── */

export const MEDICATION_STORAGE_KEY = "medication-list";

export interface Medication {
  id: string;
  name: string;           // "암로디핀"
  dosageAmount: string;   // "5" (빈 문자열이면 복용량 미입력)
  dosageUnit: string;     // "mg"
  disease: string;
  times: string[];
  active: boolean;
  scheduleType: "everyday" | "specific_days"; // 복용 주기
  scheduleDays: number[];                     // 0=일, 1=월, ..., 6=토 (specific_days 일 때만 사용)
}

const DISEASE_OPTIONS = ["고혈압", "당뇨", "고지혈증", "기타"];

const DOSAGE_UNITS = ["mg", "g", "μg", "ml", "정", "캡슐", "포", "IU", "스푼"];

function genId() {
  return Math.random().toString(36).slice(2, 10);
}

function loadMedications(): Medication[] {
  try {
    const raw = localStorage.getItem(MEDICATION_STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveMedications(list: Medication[]) {
  try {
    localStorage.setItem(MEDICATION_STORAGE_KEY, JSON.stringify(list));
    // 복약 데이터 변경 → 스케줄러 재실행
    window.dispatchEvent(new CustomEvent("notif-reschedule"));
  } catch { /* 무시 */ }
}

/** 오늘 스냅샷 저장 + 백엔드 동기화 (fire-and-forget) */
async function syncToBackend(activeNames: string[], qc: QueryClient): Promise<void> {
  const todayKey = new Date().toISOString().slice(0, 10);
  try { localStorage.setItem(medSnapshotKey(todayKey), JSON.stringify(activeNames)); } catch { /* 무시 */ }
  try {
    await upsertHealthProfile({ medications: activeNames });
    await qc.invalidateQueries({ queryKey: HEALTH_PROFILE_KEY });
  } catch (e) {
    console.warn("[MedicationManager] 백엔드 동기화 실패", e);
  }
}

/* ── 시간 태그 입력 ──────────────────────────────────── */
function TimeTagInput({
  times,
  onChange,
}: {
  times: string[];
  onChange: (v: string[]) => void;
}) {
  const [input, setInput] = useState("08:00");

  const add = () => {
    if (!input || times.includes(input)) return;
    onChange([...times, input].sort());
  };

  const remove = (t: string) => onChange(times.filter((x) => x !== t));

  return (
    <div>
      <p className="text-xs font-medium text-text-secondary mb-1.5">복용 시간</p>
      <div className="flex items-center gap-2 flex-wrap mb-2">
        <input
          type="time"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="h-9 px-3 border border-border rounded-[10px] text-sm text-text-primary bg-white focus:outline-none focus:border-brand-black"
        />
        <button
          type="button"
          onClick={add}
          className="h-9 px-3 text-sm font-semibold bg-brand-black text-white rounded-[10px]"
        >
          + 추가
        </button>
      </div>
      {times.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {times.map((t) => (
            <span
              key={t}
              className="flex items-center gap-1 px-2.5 py-1 text-xs bg-surface border border-border rounded-full"
            >
              {t}
              <button
                type="button"
                onClick={() => remove(t)}
                className="text-text-tertiary hover:text-status-danger ml-0.5"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

/* ── 약 추가/수정 폼 ─────────────────────────────────── */
const DAY_LABELS = ["일", "월", "화", "수", "목", "금", "토"];

function MedicationForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<Medication>;
  onSave: (data: Omit<Medication, "id" | "active">) => void;
  onCancel: () => void;
}) {
  const [name, setName] = useState(initial?.name ?? "");
  const [dosageAmount, setDosageAmount] = useState(initial?.dosageAmount ?? "");
  const [dosageUnit, setDosageUnit] = useState(initial?.dosageUnit ?? "mg");
  const [disease, setDisease] = useState(initial?.disease ?? "");
  const [times, setTimes] = useState<string[]>(initial?.times ?? []);
  const [scheduleType, setScheduleType] = useState<"everyday" | "specific_days">(
    initial?.scheduleType ?? "everyday"
  );
  const [scheduleDays, setScheduleDays] = useState<number[]>(initial?.scheduleDays ?? []);

  const toggleDay = (day: number) =>
    setScheduleDays((prev) =>
      prev.includes(day) ? prev.filter((d) => d !== day) : [...prev, day].sort()
    );

  const handleSubmit = () => {
    if (!name.trim()) return;
    onSave({ name: name.trim(), dosageAmount, dosageUnit, disease, times, scheduleType, scheduleDays });
  };

  return (
    <div className="mt-3 p-4 bg-surface border border-border rounded-[12px] space-y-4">
      {/* 약 이름 + 복용량 */}
      <div>
        <label className="text-xs font-medium text-text-secondary block mb-1.5">약 이름</label>
        <input
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="예: 암로디핀"
          className="w-full h-10 px-3 border border-border rounded-[10px] text-sm text-text-primary bg-white focus:outline-none focus:border-brand-black"
        />
      </div>

      {/* 복용량 (선택) */}
      <div>
        <label className="text-xs font-medium text-text-secondary block mb-1.5">
          복용량 <span className="text-text-tertiary font-normal">(선택)</span>
        </label>
        <div className="flex gap-2">
          <input
            type="number"
            value={dosageAmount}
            onChange={(e) => setDosageAmount(e.target.value)}
            placeholder="예: 5"
            min="0"
            step="any"
            className="flex-1 h-10 px-3 border border-border rounded-[10px] text-sm text-text-primary bg-white focus:outline-none focus:border-brand-black"
          />
          {/* 단위 선택 */}
          <div className="relative">
            <select
              value={dosageUnit}
              onChange={(e) => setDosageUnit(e.target.value)}
              className="h-10 pl-3 pr-8 border border-border rounded-[10px] text-sm font-medium text-text-primary bg-white appearance-none focus:outline-none focus:border-brand-black cursor-pointer"
            >
              {DOSAGE_UNITS.map((u) => (
                <option key={u} value={u}>{u}</option>
              ))}
            </select>
            <svg className="pointer-events-none absolute right-2.5 top-1/2 -translate-y-1/2 text-text-tertiary" width="12" height="12" viewBox="0 0 12 12" fill="none">
              <path d="M2 4l4 4 4-4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
            </svg>
          </div>
        </div>
        {/* 미리보기 */}
        {name.trim() && (
          <p className="mt-1.5 text-xs text-text-tertiary">
            표시 예시:{" "}
            <span className="font-medium text-text-secondary">
              {name.trim()}{dosageAmount ? ` ${dosageAmount}${dosageUnit}` : ""}
            </span>
          </p>
        )}
      </div>

      {/* 만성질환 */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-1.5">
          관련 만성질환 <span className="text-text-tertiary font-normal">(선택)</span>
        </p>
        <div className="flex flex-wrap gap-2">
          {DISEASE_OPTIONS.map((d) => (
            <button
              key={d}
              type="button"
              onClick={() => setDisease(disease === d ? "" : d)}
              className={[
                "px-3 py-1.5 text-xs rounded-full border transition-colors",
                disease === d
                  ? "bg-brand-black text-white border-brand-black"
                  : "bg-white text-text-secondary border-border hover:border-text-primary",
              ].join(" ")}
            >
              {d}
            </button>
          ))}
        </div>
      </div>

      {/* 복용 주기 */}
      <div>
        <p className="text-xs font-medium text-text-secondary mb-1.5">복용 주기</p>
        <div className="flex gap-2 mb-2">
          {(["everyday", "specific_days"] as const).map((type) => (
            <button
              key={type}
              type="button"
              onClick={() => setScheduleType(type)}
              className={[
                "px-3 py-1.5 text-xs rounded-full border transition-colors",
                scheduleType === type
                  ? "bg-brand-black text-white border-brand-black"
                  : "bg-white text-text-secondary border-border hover:border-text-primary",
              ].join(" ")}
            >
              {type === "everyday" ? "매일" : "특정 요일"}
            </button>
          ))}
        </div>
        {scheduleType === "specific_days" && (
          <div className="flex gap-1.5">
            {DAY_LABELS.map((label, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => toggleDay(idx)}
                className={[
                  "w-8 h-8 text-xs rounded-full border transition-colors font-medium",
                  scheduleDays.includes(idx)
                    ? "bg-brand-black text-white border-brand-black"
                    : "bg-white text-text-secondary border-border hover:border-text-primary",
                ].join(" ")}
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* 복용 시간 */}
      <TimeTagInput times={times} onChange={setTimes} />

      {/* 버튼 */}
      <div className="flex gap-2 pt-1">
        <button
          type="button"
          onClick={handleSubmit}
          disabled={!name.trim()}
          className="flex-1 h-10 text-sm font-semibold bg-brand-black text-white rounded-[10px] disabled:opacity-40"
        >
          저장
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 h-10 text-sm font-semibold bg-white border border-border text-text-secondary rounded-[10px]"
        >
          취소
        </button>
      </div>
    </div>
  );
}

/* ── 약 카드 ─────────────────────────────────────────── */
function MedicationCard({
  med,
  onEdit,
  onStop,
}: {
  med: Medication;
  onEdit: () => void;
  onStop: () => void;
}) {
  return (
    <div className="py-3 border-b border-border last:border-b-0">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-semibold text-text-primary">
              {med.name}
              {med.dosageAmount
                ? <span className="font-normal text-text-secondary"> {med.dosageAmount}{med.dosageUnit}</span>
                : null}
            </span>
            {med.disease && (
              <span className="px-2 py-0.5 text-[11px] font-bold bg-brand text-brand-black rounded-full">
                {med.disease}
              </span>
            )}
          </div>
          {med.times.length > 0 && (
            <p className="text-xs text-text-tertiary mt-0.5">
              {med.scheduleType === "specific_days" && med.scheduleDays.length > 0
                ? `${med.scheduleDays.map((d) => DAY_LABELS[d]).join("·")}요일`
                : "매일"}{" "}
              {med.times.join(", ")}
            </p>
          )}
        </div>
        <div className="flex gap-1.5 shrink-0">
          <button
            type="button"
            onClick={onEdit}
            className="px-3 h-7 text-xs font-medium border border-border rounded-[8px] text-text-secondary hover:border-text-primary transition-colors"
          >
            수정
          </button>
          <button
            type="button"
            onClick={onStop}
            className="px-3 h-7 text-xs font-medium border border-border rounded-[8px] text-text-secondary hover:border-status-danger hover:text-status-danger transition-colors"
          >
            중단
          </button>
        </div>
      </div>
    </div>
  );
}

/* ── 메인 컴포넌트 ───────────────────────────────────── */
export default function MedicationManager() {
  const [list, setList] = useState<Medication[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [editId, setEditId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  useEffect(() => {
    const saved = loadMedications();
    setList(saved);
    // localStorage에 데이터가 있으면 최초 1회 백엔드 동기화 + 오늘 스냅샷 저장
    if (saved.length > 0) {
      const activeNames = saved.filter((m) => m.active).map((m) => m.name);
      void syncToBackend(activeNames, queryClient);
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const persist = (next: Medication[]) => {
    setList(next);
    saveMedications(next);
    const activeNames = next.filter((m) => m.active).map((m) => m.name);
    void syncToBackend(activeNames, queryClient);
  };

  const handleAdd = (data: Omit<Medication, "id" | "active">) => {
    persist([...list, { id: genId(), active: true, ...data }]);
    setShowForm(false);
  };

  const handleEdit = (id: string, data: Omit<Medication, "id" | "active">) => {
    persist(list.map((m) => (m.id === id ? { ...m, ...data } : m)));
    setEditId(null);
  };

  const handleStop = (id: string) => {
    persist(list.filter((m) => m.id !== id));
  };

  const active = list.filter((m) => m.active);

  return (
    <section className="bg-white border border-border rounded-[16px] p-5 space-y-1">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm font-bold text-text-primary">복약 관리</p>
        {!showForm && (
          <button
            type="button"
            onClick={() => setShowForm(true)}
            className="text-xs font-semibold text-brand-black border border-border rounded-[8px] px-3 py-1.5 hover:bg-surface transition-colors"
          >
            + 새 약 추가
          </button>
        )}
      </div>

      {/* 약 목록 */}
      {active.length === 0 && !showForm && (
        <p className="text-sm text-text-tertiary py-2">등록된 복약 일정이 없어요.</p>
      )}
      {active.map((med) =>
        editId === med.id ? (
          <MedicationForm
            key={med.id}
            initial={med}
            onSave={(data) => handleEdit(med.id, data)}
            onCancel={() => setEditId(null)}
          />
        ) : (
          <MedicationCard
            key={med.id}
            med={med}
            onEdit={() => { setShowForm(false); setEditId(med.id); }}
            onStop={() => handleStop(med.id)}
          />
        )
      )}

      {/* 새 약 추가 폼 */}
      {showForm && (
        <MedicationForm
          onSave={handleAdd}
          onCancel={() => setShowForm(false)}
        />
      )}
    </section>
  );
}
