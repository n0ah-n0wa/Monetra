import { getErrorMessage } from "@/api/errors";
import { Button } from "@/components/ui/Button";

type ErrorStateProps = {
  error?: unknown;
  title?: string;
  onRetry?: () => void;
};

export function ErrorState({
  error,
  title = "Unable to load data",
  onRetry,
}: ErrorStateProps) {
  return (
    <div className="state state--error" role="alert">
      <p className="state__title">{title}</p>
      <p className="state__description">{getErrorMessage(error)}</p>
      {onRetry ? (
        <Button variant="secondary" onClick={onRetry}>
          Try again
        </Button>
      ) : null}
    </div>
  );
}
