<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Niivue } from '@niivue/niivue';
  import { Block } from "@gradio/atoms";
  import { StatusTracker } from "@gradio/statustracker";
  import type { LoadingStatus } from "@gradio/statustracker";
  import type { Gradio } from "@gradio/utils";

  interface Props {
      value?: { background_url: string | null; overlay_url: string | null } | null;
      label?: string;
      show_label?: boolean;
      loading_status?: LoadingStatus;
      elem_id?: string;
      elem_classes?: string[];
      visible?: boolean;
      height?: number;
      container?: boolean;
      scale?: number;
      min_width?: number;
      // CRITICAL: gradio prop provides i18n, autoscroll, dispatch
      gradio: Gradio<{ change: never }>;
  }

  let {
      value = null,
      label,
      show_label = true,
      loading_status,
      elem_id = "",
      elem_classes = [],
      visible = true,
      height = 500,
      container = true,
      scale = null,
      min_width = undefined,
      gradio
  }: Props = $props();

  let div_container: HTMLDivElement;
  let nv: Niivue | null = null;
  let canvas: HTMLCanvasElement;
  let initialized = false;

  onMount(async () => {
    try {
      nv = new Niivue({
        backColor: [0, 0, 0, 1],
        show3Dcrosshair: true,
        logging: false
      });

      await nv.attachToCanvas(canvas);
      await loadVolumes();
      initialized = true;
    } catch (error) {
      console.error('[NiiVue] Initialization failed:', error);
    }
  });

  onDestroy(() => {
    // Release WebGL resources and event listeners
    if (nv) {
      nv.cleanup();
      nv = null;
    }
  });

  async function loadVolumes() {
    if (!nv) return;

    // Clear existing volumes
    // nv.volumes is the internal array.
    // The safest way to clear is to remove volumes one by one or re-init.
    // However, loading new volumes usually requires removing old ones if we want a fresh state.
    // NiiVue doesn't have a clearVolumes() method exposed easily in all versions,
    // but iterating and removing works.
    while (nv.volumes.length > 0) {
         nv.removeVolume(nv.volumes[0]);
    }

    if (!value) {
        nv.drawScene();
        return;
    }

    const volumes = [];
    if (value.background_url) {
      volumes.push({ url: value.background_url });
    }
    if (value.overlay_url) {
      volumes.push({
        url: value.overlay_url,
        colormap: 'red',
        opacity: 0.5,
      });
    }

    if (volumes.length > 0) {
        await nv.loadVolumes(volumes);
    } else {
        nv.drawScene();
    }
  }

  // Reactive effect: Re-load volumes when `value` changes (only after init)
  $effect(() => {
      if (initialized && value !== undefined) {
          loadVolumes();
      }
  });

</script>

<Block
	{visible}
	variant={"solid"}
	padding={false}
	{elem_id}
	{elem_classes}
    {height}
	allow_overflow={false}
	{container}
	{scale}
	{min_width}
>
    {#if loading_status}
        <StatusTracker
            autoscroll={gradio.autoscroll}
            i18n={gradio.i18n}
            {...loading_status}
        />
    {/if}

    <div bind:this={div_container} class="niivue-container" style="height: {height}px;">
        <canvas bind:this={canvas}></canvas>
    </div>
</Block>

<style>
  .niivue-container {
    width: 100%;
    background: #000;
    position: relative;
    border-radius: var(--radius-lg);
    overflow: hidden;
  }
  canvas {
    width: 100%;
    height: 100%;
    outline: none;
    display: block;
  }
</style>
