export class ArrayMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, []);
        }
        return super.get(key);
    }
    concat(source, key) {
        this.get(key).push(...source);
    }
}

export class ObjectMap extends Map {
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, {});
        }
        return super.get(key);
    }
    assign(source, key) {
        return Object.assign(this.get(key), source);
    }
}

export class SetMap extends Map {
    stringSeparator = " ";
    get(key, insert = true) {
        if (insert && !this.has(key)) {
            this.set(key, new Set());
        }
        return super.get(key);
    }
    union(iterable, key) {
        return this.applySetOperation(iterable, key, "union");
    }
    intersection(iterable, key) {
        return this.applySetOperation(iterable, key, "intersection");
    }
    difference(iterable, key) {
        return this.applySetOperation(iterable, key, "difference");
    }
    applySetOperation(iterable, key, operation) {
        if (typeof iterable === "string") {
            iterable = iterable.split(this.stringSeparator).filter(Boolean);
        }
        return this.set(key, this.get(key)[operation](new Set(iterable)));
    }
}
