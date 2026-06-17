import apiClient from "./client";

export interface MedicationReminderResponse {
  id: number;
  medicine_name: string;
  reminder_time: string; // "HH:MM:SS"
  is_active: boolean;
  created_at: string;
}

export async function fetchMedicationReminders(): Promise<MedicationReminderResponse[]> {
  const { data } = await apiClient.get<MedicationReminderResponse[]>("/api/v1/medication-reminders");
  return data;
}

export async function createMedicationReminder(
  medicine_name: string,
  reminder_time: string,
): Promise<MedicationReminderResponse> {
  const { data } = await apiClient.post<MedicationReminderResponse>("/api/v1/medication-reminders", {
    medicine_name,
    reminder_time,
  });
  return data;
}

export async function deleteMedicationReminder(id: number): Promise<void> {
  await apiClient.delete(`/api/v1/medication-reminders/${id}`);
}

export async function updateMedicationReminder(
  id: number,
  patch: { medicine_name?: string; reminder_time?: string; is_active?: boolean },
): Promise<MedicationReminderResponse> {
  const { data } = await apiClient.patch<MedicationReminderResponse>(
    `/api/v1/medication-reminders/${id}`,
    patch,
  );
  return data;
}
