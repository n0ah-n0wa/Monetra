import { Link } from "react-router-dom";
import { PageContainer } from "@/components/layout/PageContainer";
import { routes } from "@/lib/routes";

export function NotFoundPage() {
  return (
    <PageContainer narrow>
      <div className="state state--empty">
        <p className="state__title">Page not found</p>
        <p className="state__description">The page you requested does not exist.</p>
        <Link className="btn btn--primary btn--md" to={routes.dashboard}>
          Go to dashboard
        </Link>
      </div>
    </PageContainer>
  );
}
