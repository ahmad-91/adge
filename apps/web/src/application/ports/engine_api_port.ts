import type {
  AnalyzeRequest,
  AnalyzeResponse,
  ValidationJob,
  ValidationJobRequest,
} from "@/domain/status";

export interface EngineApiPort {
  analyze(payload: AnalyzeRequest): Promise<AnalyzeResponse>;
  startValidation(payload: ValidationJobRequest): Promise<{ job_id: string; status: string }>;
  getValidationJob(jobId: string): Promise<ValidationJob>;
}
