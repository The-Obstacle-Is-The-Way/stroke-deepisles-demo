import "../../../../../assets/svelte/svelte_internal_flags_legacy.js";
import * as e from "../../../../../assets/svelte/svelte_internal_client.js";
var v = e.from_html("<img/>");
function f(s, t) {
  e.push(t, !0);
  var a = v();
  e.attribute_effect(
    a,
    (l) => ({
      src: t.src,
      class: l,
      "data-testid": t.data_testid,
      ...t.restProps
    }),
    [() => (t.class_names || []).join(" ")],
    void 0,
    void 0,
    "svelte-79s4jy"
  ), e.replay_events(a), e.event("load", a, function(l) {
    e.bubble_event.call(this, t, l);
  }), e.append(s, a), e.pop();
}
var u = e.from_html("<div><!></div>");
function p(s, t) {
  e.push(t, !1);
  let a = e.prop(t, "value", 8), l = e.prop(t, "type", 8), n = e.prop(t, "selected", 8, !1);
  e.init();
  var r = u();
  let d;
  var c = e.child(r);
  {
    var o = (i) => {
      f(i, {
        get src() {
          return e.deep_read_state(a()), e.untrack(() => a().url);
        },
        alt: ""
      });
    };
    e.if(c, (i) => {
      a() && i(o);
    });
  }
  e.reset(r), e.template_effect(() => d = e.set_class(r, 1, "container svelte-s3apn9", null, d, {
    table: l() === "table",
    gallery: l() === "gallery",
    selected: n(),
    border: a()
  })), e.append(s, r), e.pop();
}
export {
  p as default
};
