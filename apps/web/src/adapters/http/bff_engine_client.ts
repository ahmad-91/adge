import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ValidationJob,
  ValidationJobRequest,
} from "@/domain/status";
import type { EngineApiPort } from "@/application/ports/engine_api_port";

/** Calls same-origin BFF so ENGINE_API_KEY stays server-side. */
export class BffEngineClient implements EngineApiPort {
  async analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse> {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Analyze failed (${res.status})`);
    }
    return (await res.json()) as AnalyzeResponse;
  }

  async startValidation(payload: ValidationJobRequest) {
    const res = await fetch("/api/validation/jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Validation start failed (${res.status})`);
    }
    return (await res.json()) as { job_id: string; status: string };
  }

  async getValidationJob(jobId: string): Promise<ValidationJob> {
    const res = await fetch(`/api/validation/jobs/${jobId}`, { cache: "no-store" });
    if (!res.ok) {
      const text = await res.text();
      throw new Error(text || `Validation poll failed (${res.status})`);
    }
    return (await res.json()) as ValidationJob;
  }
}
