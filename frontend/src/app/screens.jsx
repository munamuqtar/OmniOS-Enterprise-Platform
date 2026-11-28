import DashboardPage from "../pages/dashboard/DashboardPage";
import LeadsPage from "../pages/crm/LeadsPage";
import LeadDetailPage from "../pages/crm/LeadDetailPage";
import ClientsPage from "../pages/crm/ClientsPage";
import ClientDetailPage from "../pages/crm/ClientDetailPage";
import OpportunitiesPage from "../pages/crm/OpportunitiesPage";
import QuotationsPage from "../pages/sales/QuotationsPage";
import QuoteFormPage from "../pages/sales/QuoteFormPage";
import QuoteDetailPage from "../pages/sales/QuoteDetailPage";
import ProjectsPage from "../pages/projects/ProjectsPage";
import ProjectDetailPage from "../pages/projects/ProjectDetailPage";
import TasksPage from "../pages/projects/TasksPage";
import TimesheetsPage from "../pages/projects/TimesheetsPage";
import InvoicesPage from "../pages/finance/InvoicesPage";
import InvoiceFormPage from "../pages/finance/InvoiceFormPage";
import InvoiceDetailPage from "../pages/finance/InvoiceDetailPage";
import PaymentsPage from "../pages/finance/PaymentsPage";
import EmployeesPage from "../pages/hr/EmployeesPage";
import EmployeeDetailPage from "../pages/hr/EmployeeDetailPage";
import RecruitmentPage from "../pages/hr/RecruitmentPage";
import CandidateDetailPage from "../pages/hr/CandidateDetailPage";
import ApplicationDetailPage from "../pages/hr/ApplicationDetailPage";
import OrganizationPage from "../pages/settings/OrganizationPage";
import BranchesPage from "../pages/settings/BranchesPage";
import UsersPage from "../pages/settings/UsersPage";
import AuditLogsPage from "../pages/system/AuditLogsPage";

// roles: null = any signed-in user, [] = Super Admin only, ["hr"] = HR (and Super Admin)
export const SCREENS = [
  { label: "Dashboard", path: "/dashboard", group: "", roles: null, element: <DashboardPage /> },

  { label: "Employees", path: "/hr/employees", group: "HR", roles: null, element: <EmployeesPage /> },
  { label: "Recruitment", path: "/hr/recruitment", group: "HR", roles: ["hr"], element: <RecruitmentPage /> },

  { label: "Leads", path: "/crm/leads", group: "CRM", roles: ["sales"], element: <LeadsPage /> },
  { label: "Clients", path: "/crm/clients", group: "CRM", roles: ["sales", "finance", "project_manager"], element: <ClientsPage /> },
  { label: "Opportunities", path: "/crm/opportunities", group: "CRM", roles: ["sales"], element: <OpportunitiesPage /> },
  { label: "Quotations", path: "/sales/quotations", group: "Sales", roles: ["sales", "finance"], element: <QuotationsPage /> },

  { label: "Projects", path: "/projects", group: "Projects", roles: ["project_manager", "sales", "finance", "employee"], element: <ProjectsPage /> },
  { label: "Tasks", path: "/tasks", group: "Projects", roles: ["project_manager", "sales", "employee"], element: <TasksPage /> },
  { label: "Timesheets", path: "/timesheets", group: "Projects", roles: ["employee", "project_manager", "hr", "finance"], element: <TimesheetsPage /> },

  { label: "Invoices", path: "/finance/invoices", group: "Finance", roles: ["finance", "sales", "project_manager"], element: <InvoicesPage /> },
  { label: "Payments", path: "/finance/payments", group: "Finance", roles: ["finance"], element: <PaymentsPage /> },

  { label: "Organization", path: "/settings/organization", group: "Settings", roles: [], element: <OrganizationPage /> },
  { label: "Branches", path: "/settings/branches", group: "Settings", roles: [], element: <BranchesPage /> },
  { label: "Users", path: "/settings/users", group: "Settings", roles: [], element: <UsersPage /> },
  { label: "Audit Logs", path: "/audit-logs", group: "System", roles: ["hr", "finance", "project_manager"], element: <AuditLogsPage /> },
];

// Detail and form pages. They are not in the sidebar, but they are guarded the same way.
export const EXTRA_ROUTES = [
  { path: "/crm/leads/:id", roles: ["sales"], element: <LeadDetailPage /> },
  { path: "/crm/clients/:id", roles: ["sales", "finance", "project_manager"], element: <ClientDetailPage /> },
  { path: "/sales/quotations/new", roles: ["sales"], element: <QuoteFormPage /> },
  { path: "/sales/quotations/:id/edit", roles: ["sales"], element: <QuoteFormPage /> },
  { path: "/sales/quotations/:id", roles: ["sales", "finance"], element: <QuoteDetailPage /> },
  { path: "/projects/:id", roles: ["project_manager", "sales", "finance", "employee"], element: <ProjectDetailPage /> },
  { path: "/finance/invoices/new", roles: ["finance"], element: <InvoiceFormPage /> },
  { path: "/finance/invoices/:id", roles: ["finance", "sales", "project_manager"], element: <InvoiceDetailPage /> },
  { path: "/hr/employees/:id", roles: null, element: <EmployeeDetailPage /> },
  { path: "/hr/recruitment/applications/:id", roles: ["hr"], element: <ApplicationDetailPage /> },
  { path: "/hr/recruitment/candidates/:id", roles: ["hr"], element: <CandidateDetailPage /> },
];

export const screenFor = (pathname) =>
  SCREENS.find((s) => pathname === s.path || pathname.startsWith(`${s.path}/`));