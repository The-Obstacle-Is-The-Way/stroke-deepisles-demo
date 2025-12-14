import type { SegmentationResult, CasesResponse } from "../types";

export const mockCases: string[] = [
  "sub-stroke0001",
  "sub-stroke0002",
  "sub-stroke0003",
];

export const mockCasesResponse: CasesResponse = {
  cases: mockCases,
};

export const mockSegmentationResult: SegmentationResult = {
  // URLs match actual API contract: /files/{jobId}/{caseId}/{filename}
  dwiUrl: "http://localhost:7860/files/test-job-123/sub-stroke0001/dwi.nii.gz",
  predictionUrl: "http://localhost:7860/files/test-job-123/sub-stroke0001/prediction.nii.gz",
  metrics: {
    caseId: "sub-stroke0001",
    diceScore: 0.847,
    volumeMl: 15.32,
    elapsedSeconds: 12.5,
  },
};
