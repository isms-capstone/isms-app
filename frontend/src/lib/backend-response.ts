/** Keep an upstream error's status without exposing its non-JSON traceback. */
export async function readBackendJson(response: Response) {
  const text = await response.text();
  try {
    return {
      data: JSON.parse(text) as unknown,
      status: response.status,
      validJson: true,
    };
  } catch {
    return {
      data: {
        detail: response.ok
          ? "ยังยืนยันผลการบันทึกไม่ได้ กรุณาโหลดไทม์ไลน์ก่อนบันทึกซ้ำ"
          : `Backend ประมวลผลไม่สำเร็จ (HTTP ${response.status}) กรุณาลองใหม่ภายหลัง`,
        code: response.ok ? "invalid_backend_response" : "backend_error",
      },
      status: response.ok ? 502 : response.status,
      validJson: false,
    };
  }
}
