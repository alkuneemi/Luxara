/** @odoo-module **/
import { Component, useState, onMounted, useService } from "@odoo/owl";
import { registry } from "@web/core/registry";

class AmeenDashboard extends Component {
    static template = "insurance_broker_suite.AmeenDashboard";

    setup() {
        this.action = useService("action");
        this.orm    = useService("orm");
        this.state  = useState({
            dateLabel: new Date().toLocaleDateString("ar-OM", { weekday:"long", year:"numeric", month:"long", day:"numeric" }),
            totalApplications:    0,
            pendingApplications:  0,
            completedApplications:0,
            totalOpportunities:   0,
            activePolicies:       0,
            totalPolicies:        0,
            expiringIn60Days:     0,
            commissionReceived:   "0.000",
            openClaims:           0,
            totalClients:         0,
            openRfqs:             0,
            recentApplications:   [],
            oppByStage:           [],
        });
        onMounted(() => this._loadAll());
    }

    async _loadAll() {
        try {
            const today = new Date();
            const in60  = new Date(today); in60.setDate(in60.getDate() + 60);
            const fmt   = d => d.toISOString().slice(0,10);

            const [apps, pending, done, opps, policies, expiring, clients, rfqs, claims, commissions, stages, recentRaw] = await Promise.all([
                this.orm.searchCount("insurance.application", []),
                this.orm.searchCount("insurance.application", [["state","in",["new","in_progress"]]]),
                this.orm.searchCount("insurance.application", [["state","=","done"]]),
                this.orm.searchCount("insurance.opportunity",  []),
                this.orm.searchCount("insurance.policy",       [["state","=","active"]]),
                this.orm.searchCount("insurance.policy",       [["state","=","active"],["end_date","<=",fmt(in60)],["end_date",">=",fmt(today)]]),
                this.orm.searchCount("insurance.client",       []),
                this.orm.searchCount("insurance.rfq",          [["state","in",["draft","sent"]]]),
                this.orm.searchCount("insurance.claim",        [["state","in",["new","open","pending"]]]),
                this.orm.readGroup("insurance.commission",     [["state","=","done"]], ["amount_received:sum"], []),
                this.orm.searchRead("crm.stage", [], ["name","sequence"], {order:"sequence asc", limit:10}),
                this.orm.searchRead("insurance.application", [], ["partner_name","ins_type_id","state","create_date"], {order:"create_date desc", limit:8}),
            ]);

            this.state.totalApplications     = apps;
            this.state.pendingApplications   = pending;
            this.state.completedApplications = done;
            this.state.totalOpportunities    = opps;
            this.state.activePolicies        = policies;
            this.state.expiringIn60Days      = expiring;
            this.state.totalClients          = clients;
            this.state.openRfqs              = rfqs;
            this.state.openClaims            = claims;
            this.state.commissionReceived    = ((commissions[0] && commissions[0].amount_received) || 0).toFixed(3) + " OMR";

            const stageColors = ["#344B9B","#5CAFE4","#84CFFF","#10B981","#F59E0B","#EF4444","#8B5CF6","#6B7280"];
            this.state.oppByStage = stages.slice(0,6).map((s,i) => ({ stage: s.id, label: s.name, count: 0, color: stageColors[i % stageColors.length] }));

            const stateMap = { new:"جديد", in_progress:"قيد المعالجة", done:"مكتمل", cancelled:"ملغي" };
            const urgencyMap = { new:"low", in_progress:"medium", done:"ok", cancelled:"critical" };
            this.state.recentApplications = recentRaw.map(a => ({
                id: a.id,
                client_name: a.partner_name || "—",
                type_label:  (a.ins_type_id && a.ins_type_id[1]) || "—",
                state_label: stateMap[a.state] || a.state,
                urgency:     urgencyMap[a.state] || "low",
                create_date: a.create_date ? a.create_date.slice(0,10) : "—",
            }));

            // Opp count by stage
            if (this.state.oppByStage.length) {
                const oppCounts = await this.orm.readGroup("insurance.opportunity", [], ["stage_id"], ["stage_id"]);
                oppCounts.forEach(g => {
                    const sid = g.stage_id && g.stage_id[0];
                    const found = this.state.oppByStage.find(s => s.stage === sid);
                    if (found) found.count = g.stage_id_count;
                });
            }
        } catch(e) {
            console.warn("[AmeenDashboard] load error", e);
        }
    }

    // ── Navigation helpers ──
    openApplications()        { this.action.doAction({ type:"ir.actions.act_window", name:"الطلبات", res_model:"insurance.application", views:[[false,"list"],[false,"form"]] }); }
    openPendingApplications() { this.action.doAction({ type:"ir.actions.act_window", name:"طلبات معلقة", res_model:"insurance.application", domain:[["state","in",["new","in_progress"]]], views:[[false,"list"],[false,"form"]] }); }
    openCompletedApplications(){ this.action.doAction({ type:"ir.actions.act_window", name:"طلبات مكتملة", res_model:"insurance.application", domain:[["state","=","done"]], views:[[false,"list"],[false,"form"]] }); }
    openPolicies()            { this.action.doAction({ type:"ir.actions.act_window", name:"الوثائق النشطة", res_model:"insurance.policy", domain:[["state","=","active"]], views:[[false,"list"],[false,"form"]] }); }
    openExpiringPolicies()    { this.action.doAction({ name:"insurance_broker_suite.action_insurance_policy_expiring" }); }
    openClients()             { this.action.doAction({ name:"insurance_broker_suite.action_insurance_client" }); }
    openOpportunities()       { this.action.doAction({ name:"insurance_broker_suite.action_insurance_opportunity_new" }); }
    openCommissions()         { this.action.doAction({ name:"insurance_broker_suite.action_insurance_commission" }); }
    openClaims()              { this.action.doAction({ name:"insurance_broker_suite.action_insurance_claim" }); }
    openRfqs()                { this.action.doAction({ name:"insurance_broker_suite.action_insurance_rfq" }); }
}

registry.category("actions").add("ameen_broker_dashboard", AmeenDashboard);
