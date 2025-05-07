export async function analyze(file: File) {
    const body = new FormData();
    body.append("csv", file);
    const res = await fetch(
      process.env.NEXT_PUBLIC_API_URL + "/analyze",
      { method: "POST", body }
    );
    return res.json();
  }
  