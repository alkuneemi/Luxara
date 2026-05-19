/** @odoo-module **/

import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

const POLICY_TYPE_LABELS = {
    motor:                "Motor",
    medical:              "Medical",
    life:                 "Life",
    property:             "Property",
    marine:               "Marine",
    group_life:           "Group Life",
    workmen_compensation: "Workmen Comp.",
};

const CLAIM_STATUS_META = {
    reported:            { label: "Reported",         color: "#64748b" },
    documents_collected: { label: "Docs Collected",   color: "#0891b2" },
    submitted:           { label: "Submitted",        color: "#3b82f6" },
    under_assessment:    { label: "Under Assessment", color: "#ca8a04" },
    approved:            { label: "Approved",         color: "#22c55e" },
    rejected:            { label: "Rejected",         color: "#ef4444" },
    settled:             { label: "Settled",          color: "#6366f1" },
};

const OPP_STAGE_META = {
    new:                   { label: "New",               color: "#64748b" },
    qualified:             { label: "Qualified",         color: "#3b82f6" },
    quote_requested:       { label: "Quote Requested",   color: "#f59e0b" },
    application_submitted: { label: "App. Submitted",    color: "#8b5cf6" },
    won:                   { label: "Won",               color: "#10b981" },
    lost:                  { label: "Lost",              color: "#ef4444" },
};

class InsuranceBrokerDashboard extends Component {
    static template = "insurance_broker_suite.Dashboard";

    setup() {
        this.orm    = useService("orm");
        this.action = useService("action");

        this.state = useState({
            activePolicies:        0,
            totalPolicies:         0,
            expiringIn60Days:      0,
            totalPremiumYTD:       "OMR 0",
            renewalRate:           "0%",
            policiesByType:        [],
            renewals:              [],
            totalClients:          0,
            corporateClients:      0,
            personalClients:       0,
            openClaims:            0,
            claimsByStatus:        [],
            openRfqs:              0,
            pendingApplications:   0,
            totalOpportunities:    0,
            wonOpportunities:      0,
            oppByStage:            [],
            commissionReceived:    "OMR 0",
            commissionExpected:    "OMR 0",
            commissionOutstanding: "OMR 0",
            overdueCommissions:    0,
            dateLabel: new Date().toLocaleDateString("en-GB", {
                weekday: "long",
                day: "2-digit",
                month: "long",
                year: "numeric",
            }),
        });

        onWillStart(async () => {
            await this._loadDashboardData();
        });
    }

    // ── HELPERS ──────────────────────────────────────────────────────

    _fmt(val) {
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "OMR",
            maximumFractionDigits: 0,
        }).format(val || 0);
    }

    _today() {
        return new Date().toISOString().split("T")[0];
    }

    _addDays(n) {
        const d = new Date();
        d.setDate(d.getDate() + n);
        return d.toISOString().split("T")[0];
    }

    // ── DATA LOADING ─────────────────────────────────────────────────

    async _loadDashboardData() {
        const todayStr    = this._today();
        const in60DaysStr = this._addDays(60);
        const startOfYear = `${new Date().getFullYear()}-01-01`;

        // 1. Policy counts
        const [
            activePolicies,
            totalPolicies,
            expiringPolicies,
            renewedPolicies,
        ] = await Promise.all([
            this.orm.searchCount("insurance.policy", [["status", "=", "active"]]),
            this.orm.searchCount("insurance.policy", []),
            this.orm.searchCount("insurance.policy", [
                ["status", "=", "active"],
                ["expiry_date", ">=", todayStr],
                ["expiry_date", "<=", in60DaysStr],
            ]),
            this.orm.searchCount("insurance.policy", [["status", "=", "renewed"]]),
        ]);

        // 2. Operational counts
        const [
            totalClients,
            corporateClients,
            personalClients,
            openClaims,
            openRfqs,
            pendingApplications,
            totalOpportunities,
            wonOpportunities,
            overdueCommissions,
        ] = await Promise.all([
            this.orm.searchCount("insurance.client", []),
            this.orm.searchCount("insurance.client", [["category", "=", "corporate"]]),
            this.orm.searchCount("insurance.client", [["category", "=", "personal"]]),
            this.orm.searchCount("insurance.claim",  [["status", "not in", ["settled", "rejected"]]]),
            this.orm.searchCount("insurance.rfq",    [["status", "not in", ["closed"]]]),
            this.orm.searchCount("insurance.application", [
                ["status", "in", ["submitted", "under_review", "info_required"]],
            ]),
            this.orm.searchCount("insurance.opportunity", []),
            this.orm.searchCount("insurance.opportunity", [["stage", "=", "won"]]),
            this.orm.searchCount("insurance.commission",  [["status", "=", "overdue"]]),
        ]);

        // 3. Aggregates
        const [premiumData, commData] = await Promise.all([
            this.orm.call("insurance.policy", "read_group", [
                [["issue_date", ">=", startOfYear]],
                ["net_premium:sum"],
                [],
            ]),
            this.orm.call("insurance.commission", "read_group", [
                [],
                ["expected_amount:sum", "received_amount:sum"],
                [],
            ]),
        ]);

        // 4. Policies by type (active only)
        const policyTypeGroups = await this.orm.call(
            "insurance.policy", "read_group",
            [[["status", "=", "active"]], ["insurance_type"], ["insurance_type"]],
        );
        const maxTypeCount = Math.max(1, ...policyTypeGroups.map(g => g.insurance_type_count || 0));
        const policiesByType = policyTypeGroups
            .map(g => ({
                type:  g.insurance_type || "default",
                label: POLICY_TYPE_LABELS[g.insurance_type] || g.insurance_type || "Other",
                count: g.insurance_type_count || 0,
                pct:   Math.round(((g.insurance_type_count || 0) / maxTypeCount) * 100),
            }))
            .sort((a, b) => b.count - a.count);

        // 5. Claims by status
        const claimGroups = await this.orm.call(
            "insurance.claim", "read_group",
            [[], ["status"], ["status"]],
        );
        const maxClaimCount = Math.max(1, ...claimGroups.map(g => g.status_count || 0));
        const claimsByStatus = claimGroups
            .map(g => {
                const meta = CLAIM_STATUS_META[g.status] || { label: g.status, color: "#64748b" };
                return {
                    status: g.status,
                    label:  meta.label,
                    color:  meta.color,
                    count:  g.status_count || 0,
                    pct:    Math.round(((g.status_count || 0) / maxClaimCount) * 100),
                };
            })
            .sort((a, b) => b.count - a.count);

        // 6. Opportunities by stage
        const oppGroups = await this.orm.call(
            "insurance.opportunity", "read_group",
            [[], ["stage"], ["stage"]],
        );
        const oppByStage = oppGroups.map(g => {
            const meta = OPP_STAGE_META[g.stage] || { label: g.stage, color: "#64748b" };
            return {
                stage: g.stage,
                label: meta.label,
                color: meta.color,
                count: g.stage_count || 0,
            };
        });

        // 7. Upcoming renewals (next 60 days, ordered soonest first)
        const renewalRecords = await this.orm.searchRead(
            "insurance.policy",
            [
                ["status", "=", "active"],
                ["expiry_date", ">=", todayStr],
                ["expiry_date", "<=", in60DaysStr],
            ],
            ["policy_number", "client_id", "insurance_type", "expiry_date"],
            { limit: 10, order: "expiry_date asc" },
        );

        const now = new Date();
        const renewals = renewalRecords.map(p => {
            const daysLeft = Math.round((new Date(p.expiry_date) - now) / 86400000);
            return {
                id:            p.id,
                policy_number: p.policy_number,
                client_name:   Array.isArray(p.client_id) ? p.client_id[1] : (p.client_id || "—"),
                type_label:    POLICY_TYPE_LABELS[p.insurance_type] || p.insurance_type || "—",
                expiry_date:   p.expiry_date,
                days_left:     daysLeft,
                urgency:       daysLeft <= 15 ? "urgent" : daysLeft <= 30 ? "warning" : "ok",
            };
        });

        // 8. Derived values
        const totalPremiumYTD = premiumData[0]?.net_premium    || 0;
        const commExpected    = commData[0]?.expected_amount    || 0;
        const commReceived    = commData[0]?.received_amount    || 0;
        const commOutstanding = commExpected - commReceived;
        const renewalRate     = totalPolicies > 0
            ? Math.round((renewedPolicies / totalPolicies) * 100)
            : 0;

        // 9. Write to state
        Object.assign(this.state, {
            activePolicies,
            totalPolicies,
            expiringIn60Days:      expiringPolicies,
            renewalRate:           `${renewalRate}%`,
            totalPremiumYTD:       this._fmt(totalPremiumYTD),
            policiesByType,
            renewals,
            totalClients,
            corporateClients,
            personalClients,
            openClaims,
            claimsByStatus,
            openRfqs,
            pendingApplications,
            totalOpportunities,
            wonOpportunities,
            oppByStage,
            commissionExpected:    this._fmt(commExpected),
            commissionReceived:    this._fmt(commReceived),
            commissionOutstanding: this._fmt(commOutstanding),
            overdueCommissions,
        });
    }

    // ── NAVIGATION HANDLERS ───────────────────────────────────────────

    openActivePolicies() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Active Policies",
            res_model: "insurance.policy",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "active"]],
        });
    }

    openPoliciesExpiring() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Expiring Policies",
            res_model: "insurance.policy",
            views: [[false, "list"], [false, "form"]],
            domain: [["is_expiring_soon", "=", true], ["status", "=", "active"]],
        });
    }

    openRenewedPolicies() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Renewed Policies",
            res_model: "insurance.policy",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "renewed"]],
        });
    }

    openPremiums() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "All Policies",
            res_model: "insurance.policy",
            views: [[false, "list"], [false, "form"]],
            domain: [],
        });
    }

    openPolicy(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Policy",
            res_model: "insurance.policy",
            views: [[false, "form"]],
            res_id: id,
        });
    }

    openClients() {
        this.action.doAction("insurance_broker_suite.action_insurance_client");
    }

    openClaims() {
        this.action.doAction("insurance_broker_suite.action_insurance_claim");
    }

    openRfqs() {
        this.action.doAction("insurance_broker_suite.action_insurance_rfq");
    }

    openOnlineApplications() {
        this.action.doAction("insurance_broker_suite.action_insurance_application");
    }

    openOpportunities() {
        this.action.doAction("insurance_broker_suite.action_insurance_opportunity");
    }

    openCommissions() {
        this.action.doAction("insurance_broker_suite.action_insurance_commission");
    }

    openOverdueCommissions() {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: "Overdue Commissions",
            res_model: "insurance.commission",
            views: [[false, "list"], [false, "form"]],
            domain: [["status", "=", "overdue"]],
        });
    }

    openCustomerWebsite() {
        window.open("/insurance", "_blank");
    }

    openProviderPortal() {
        window.open("/insurance/provider", "_blank");
    }
}

registry.category("actions").add("insurance_broker_dashboard", InsuranceBrokerDashboard);
