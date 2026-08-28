import { apiClient } from "@/api/client";

export async function downloadTransactionsExport(): Promise<void> {
  const blob = await apiClient.getBlob("/exports/transactions", {
    headers: { Accept: "text/csv" },
  });
  const objectUrl = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = objectUrl;
  link.download = "monetra-transactions.csv";
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(objectUrl);
}
