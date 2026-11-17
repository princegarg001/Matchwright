import { validateFile } from "../components/FileDrop";

describe("validateFile", () => {
  it("accepts resumes and rejects other files", () => {
    expect(validateFile(new File(["x"], "cv.pdf"))).toBeNull();
    expect(validateFile(new File(["x"], "cv.DOCX"))).toBeNull();
    expect(validateFile(new File(["x"], "photo.png"))).toMatch(/PDF, DOCX or TXT/);
  });
  it("rejects files over 2 MB", () => {
    const big = new File([new Uint8Array(2 * 1024 * 1024 + 1)], "big.pdf");
    expect(validateFile(big)).toMatch(/2 MB/);
  });
});
