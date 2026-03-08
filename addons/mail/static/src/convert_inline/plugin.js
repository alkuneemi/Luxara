export class Plugin {
    static id = "";
    static dependencies = [];
    static shared = [];
    static defaultConfig = {};

    resources;

    constructor(context) {
        this.config = context.config;
        this.services = context.services;
        this.dependencies = context.dependencies;
        this.getResource = context.getResource;
        this.trigger = context.trigger;
        this.triggerAsync = context.triggerAsync;
        this.delegateTo = context.delegateTo;
        this.processThrough = context.processThrough;
        this.checkPredicates = context.checkPredicates;

        this._cleanups = [];
        this.isDestroyed = false;
    }

    setup() {}

    destroy() {
        for (const cleanup of this._cleanups) {
            cleanup();
        }
        this.isDestroyed = true;
    }
}
