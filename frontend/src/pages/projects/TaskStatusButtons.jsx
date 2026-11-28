import { useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { useAuth } from "../../app/providers/auth-context";
import { useApiAction } from "../../hooks/useApiAction";
import { titleCase } from "../../utils/format";
import { taskMoves } from "../../utils/workflow";

export default function TaskStatusButtons({ task }) {
  const { user, hasRole } = useAuth();
  const qc = useQueryClient();
  const isManager = hasRole("project_manager");
  const canChange = isManager || user.roles.includes("employee");
  const action = useApiAction(
    async (status) => unwrap(await api.post(`/tasks/${task.id}/status/`, { status })),
    { onSuccess: () => { qc.invalidateQueries({ queryKey: ["/tasks/"] }); qc.invalidateQueries({ queryKey: ["/projects/"] }); } }
  );
  if (!canChange) return null;
  return (
    <div className="stack" onClick={(e) => e.stopPropagation()}>
      <div className="page-actions">
        {taskMoves(task.status, isManager).map((s) => (
          <button key={s} className="btn btn-ghost" disabled={action.busy} onClick={() => { action.reset(); action.run(s); }}>
            → {titleCase(s)}
          </button>
        ))}
      </div>
      {action.error && <small className="error-text" role="alert">{action.error.message}</small>}
    </div>
  );
}
