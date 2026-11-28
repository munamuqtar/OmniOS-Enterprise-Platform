import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, unwrap } from "../../services/api/client";
import { formatDateTime } from "../../utils/format";
import EmptyState from "../common/EmptyState";
import { Bell } from "lucide-react";

export default function NotificationBell() {
  const [open, setOpen] = useState(false);
  const qc = useQueryClient();

  const count = useQuery({
    queryKey: ["notifications", "count"],
    queryFn: async () => unwrap(await api.get("/notifications/unread-count/")).unread,
    refetchInterval: 60000,
  });
  const list = useQuery({
    queryKey: ["notifications", "list"], enabled: open,
    queryFn: async () => unwrap(await api.get("/notifications/")).results,
  });
  const refresh = () => qc.invalidateQueries({ queryKey: ["notifications"] });
  const read = useMutation({ mutationFn: (id) => api.post(`/notifications/${id}/read/`), onSuccess: refresh });
  const readAll = useMutation({ mutationFn: () => api.post("/notifications/read-all/"), onSuccess: refresh });
  const unread = count.data ?? 0;

  return (
    <div className="bell">
      <button className="icon-btn" onClick={() => setOpen((o) => !o)} aria-label={`Notifications, ${unread} unread`}>
        <Bell size={20} />{unread > 0 && <span className="dot">{unread > 99 ? "99+" : unread}</span>}
      </button>
      {open && (
        <div className="dropdown" role="menu">
          <div className="dropdown-head">
            <strong>Notifications</strong>
            <button className="link" disabled={!unread} onClick={() => readAll.mutate()}>Mark all read</button>
          </div>
          {list.data?.length === 0 && <EmptyState title="You're all caught up" />}
          {list.data?.map((n) => (
            <button key={n.id} className={`note ${n.is_read ? "" : "unread"}`}
                    onClick={() => !n.is_read && read.mutate(n.id)}>
              <strong>{n.title}</strong>
              {n.message && <span>{n.message}</span>}
              <small className="muted">{formatDateTime(n.created_at)}</small>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}