/**
 * CyberEval - Interactive Claim-to-Evidence Directed Graph Visualizer (Innovation 1)
 * Renders bipartite proposition networks linking forensic evidence to AI claims.
 * Complies with strict security rules: uses textContent and SVG namespaces, no unsafe innerHTML.
 */

class ClaimGraphVisualizer {
  constructor(svgElementId, detailsCardId) {
    this.svg = document.getElementById(svgElementId);
    this.detailsCard = document.getElementById(detailsCardId);
    this.ns = "http://www.w3.org/2000/svg";
  }

  render(graphData) {
    if (!this.svg) return;
    this.svg.replaceChildren(); // Safe DOM clear

    if (!graphData || !graphData.nodes || graphData.nodes.length === 0) {
      const text = document.createElementNS(this.ns, "text");
      text.setAttribute("x", "50%");
      text.setAttribute("y", "50%");
      text.setAttribute("text-anchor", "middle");
      text.setAttribute("fill", "#64748b");
      text.textContent = "No graph data available for this evaluation response.";
      this.svg.appendChild(text);
      return;
    }

    const width = this.svg.clientWidth || 900;
    const height = this.svg.clientHeight || 520;

    // Separate nodes into two columns: Evidence on left, Claims on right, Traps on bottom right
    const evidenceNodes = graphData.nodes.filter(n => n.node_type === "evidence");
    const claimNodes = graphData.nodes.filter(n => n.node_type === "claim");
    const trapNodes = graphData.nodes.filter(n => n.node_type === "hallucination_trap");

    const positions = new Map();

    // Layout Evidence Column (Left)
    const evStep = height / (evidenceNodes.length + 1);
    evidenceNodes.forEach((node, i) => {
      positions.set(node.id, {
        x: width * 0.18,
        y: evStep * (i + 1),
        node: node
      });
    });

    // Layout Claims Column (Right)
    const claimStep = height / (claimNodes.length + 1);
    claimNodes.forEach((node, i) => {
      positions.set(node.id, {
        x: width * 0.75,
        y: claimStep * (i + 1),
        node: node
      });
    });

    // Layout Traps (Far Right Bottom)
    trapNodes.forEach((node, i) => {
      positions.set(node.id, {
        x: width * 0.82,
        y: height * 0.85 - (i * 45),
        node: node
      });
    });

    // Add SVG marker definition for directed arrows
    const defs = document.createElementNS(this.ns, "defs");
    const marker = document.createElementNS(this.ns, "marker");
    marker.setAttribute("id", "arrowhead");
    marker.setAttribute("markerWidth", "8");
    marker.setAttribute("markerHeight", "6");
    marker.setAttribute("refX", "7");
    marker.setAttribute("refY", "3");
    marker.setAttribute("orient", "auto");
    const arrowPath = document.createElementNS(this.ns, "polygon");
    arrowPath.setAttribute("points", "0 0, 8 3, 0 6");
    arrowPath.setAttribute("fill", "#64748b");
    marker.appendChild(arrowPath);
    defs.appendChild(marker);
    this.svg.appendChild(defs);

    // 1. Render Directed Edges
    const edgeGroup = document.createElementNS(this.ns, "g");
    edgeGroup.setAttribute("class", "graph-edges");

    graphData.edges.forEach(edge => {
      const srcPos = positions.get(edge.source);
      const tgtPos = positions.get(edge.target);

      if (srcPos && tgtPos) {
        const line = document.createElementNS(this.ns, "line");
        line.setAttribute("x1", srcPos.x);
        line.setAttribute("y1", srcPos.y);
        line.setAttribute("x2", tgtPos.x);
        line.setAttribute("y2", tgtPos.y);
        
        let strokeColor = "#38bdf8"; // default cyan
        let strokeDash = "none";

        if (edge.relation === "SUPPORTS") {
          strokeColor = "#10b981"; // emerald
        } else if (edge.relation === "FALLS_INTO_TRAP") {
          strokeColor = "#f43f5e"; // rose
          strokeDash = "4,4";
        } else if (edge.relation === "UNSUPPORTED_LEAP") {
          strokeColor = "#f59e0b"; // amber
          strokeDash = "3,3";
        }

        line.setAttribute("stroke", strokeColor);
        line.setAttribute("stroke-width", "2");
        line.setAttribute("stroke-dasharray", strokeDash);
        line.setAttribute("marker-end", "url(#arrowhead)");
        line.setAttribute("opacity", "0.75");
        edgeGroup.appendChild(line);
      }
    });
    this.svg.appendChild(edgeGroup);

    // 2. Render Nodes
    const nodeGroup = document.createElementNS(this.ns, "g");
    nodeGroup.setAttribute("class", "graph-nodes");

    positions.forEach((pos, id) => {
      const node = pos.node;
      const g = document.createElementNS(this.ns, "g");
      g.setAttribute("class", "graph-node");
      g.setAttribute("cursor", "pointer");
      g.addEventListener("click", () => this.showNodeDetails(node));

      let fillColor = "#06b6d4"; // Evidence (Cyan)
      let r = 16;

      if (node.node_type === "claim") {
        r = 18;
        if (node.status === "SUPPORTED") {
          fillColor = "#10b981"; // Emerald
        } else if (node.status === "UNSUPPORTED") {
          fillColor = "#f59e0b"; // Amber
        } else {
          fillColor = "#f43f5e"; // Rose
        }
      } else if (node.node_type === "hallucination_trap") {
        fillColor = "#f43f5e";
        r = 20;
      }

      // Outer glow circle
      const glow = document.createElementNS(this.ns, "circle");
      glow.setAttribute("cx", pos.x);
      glow.setAttribute("cy", pos.y);
      glow.setAttribute("r", r + 4);
      glow.setAttribute("fill", fillColor);
      glow.setAttribute("opacity", "0.25");
      g.appendChild(glow);

      // Main circle
      const circle = document.createElementNS(this.ns, "circle");
      circle.setAttribute("cx", pos.x);
      circle.setAttribute("cy", pos.y);
      circle.setAttribute("r", r);
      circle.setAttribute("fill", fillColor);
      circle.setAttribute("stroke", "#ffffff");
      circle.setAttribute("stroke-width", "1.5");
      g.appendChild(circle);

      // Label
      const label = document.createElementNS(this.ns, "text");
      label.setAttribute("x", pos.x + (node.node_type === "evidence" ? -24 : 24));
      label.setAttribute("y", pos.y + 5);
      label.setAttribute("text-anchor", node.node_type === "evidence" ? "end" : "start");
      label.setAttribute("fill", "#f8fafc");
      label.setAttribute("font-size", "12px");
      label.setAttribute("font-family", "Inter, sans-serif");
      label.setAttribute("font-weight", "600");
      label.textContent = node.label;
      g.appendChild(label);

      nodeGroup.appendChild(g);
    });

    this.svg.appendChild(nodeGroup);
  }

  showNodeDetails(node) {
    if (!this.detailsCard) return;
    this.detailsCard.replaceChildren();

    const titleEl = document.createElement("strong");
    titleEl.textContent = `[${node.node_type.toUpperCase()}] ${node.label} (${node.status || "OBSERVED"})`;
    titleEl.style.display = "block";
    titleEl.style.color = node.status === "SUPPORTED" ? "#34d399" : (node.status === "UNSUPPORTED" ? "#fbbf24" : "#38bdf8");
    titleEl.style.marginBottom = "0.4rem";
    this.detailsCard.appendChild(titleEl);

    if (node.node_type === "claim") {
      const stmtP = document.createElement("p");
      stmtP.textContent = `Statement: "${node.details?.statement || 'N/A'}"`;
      stmtP.style.marginBottom = "0.3rem";
      this.detailsCard.appendChild(stmtP);

      if (node.details?.gap) {
        const gapP = document.createElement("p");
        gapP.style.color = "#fbbf24";
        gapP.textContent = `⚠️ Evidence Gap: ${node.details.gap}`;
        this.detailsCard.appendChild(gapP);
      }

      if (node.details?.correction) {
        const corrP = document.createElement("p");
        corrP.style.color = "#94a3b8";
        corrP.textContent = `💡 Recommended Correction: ${node.details.correction}`;
        this.detailsCard.appendChild(corrP);
      }
    } else if (node.node_type === "evidence") {
      const payloadP = document.createElement("pre");
      payloadP.style.background = "rgba(0,0,0,0.5)";
      payloadP.style.padding = "0.5rem";
      payloadP.style.borderRadius = "4px";
      payloadP.style.fontSize = "0.75rem";
      payloadP.style.overflowX = "auto";
      payloadP.textContent = JSON.stringify(node.details, null, 2);
      this.detailsCard.appendChild(payloadP);
    }
  }
}
