/**
 * D3.js Force-Directed Graph for Relationship Visualization
 */

function renderSearchGraph(relationships) {
    const container = document.getElementById('search-graph');
    container.innerHTML = '';
    if (!relationships || !relationships.nodes || relationships.nodes.length < 2) {
        container.innerHTML = '<div class="empty-state"><p>İlişki görselleştirmesi için yeterli sonuç yok</p></div>';
        return;
    }
    renderForceGraph(container, relationships.nodes, relationships.edges, false);
}

function renderForceGraph(container, nodes, edges, isExplore = false) {
    const width = container.clientWidth;
    const height = container.clientHeight || 500;

    // Color scale for categories
    const colorScale = d3.scaleOrdinal()
        .domain([...new Set(nodes.map(n => n.category || 'Diğer'))])
        .range(['#6366f1', '#8b5cf6', '#a855f7', '#ec4899', '#f43f5e', '#f97316', '#eab308', '#22c55e', '#14b8a6', '#3b82f6']);

    // Create SVG
    const svg = d3.select(container)
        .append('svg')
        .attr('width', width)
        .attr('height', height)
        .attr('viewBox', [0, 0, width, height]);

    // Add zoom behavior
    const g = svg.append('g');
    svg.call(d3.zoom()
        .scaleExtent([0.3, 4])
        .on('zoom', (event) => g.attr('transform', event.transform)));

    // Create simulation
    const simulation = d3.forceSimulation(nodes)
        .force('link', d3.forceLink(edges).id(d => d.id).distance(d => 150 - d.weight * 80))
        .force('charge', d3.forceManyBody().strength(-300))
        .force('center', d3.forceCenter(width / 2, height / 2))
        .force('collision', d3.forceCollide().radius(40));

    // Add gradient definitions
    const defs = svg.append('defs');
    const gradient = defs.append('linearGradient')
        .attr('id', 'linkGradient')
        .attr('gradientUnits', 'userSpaceOnUse');
    gradient.append('stop').attr('offset', '0%').attr('stop-color', '#6366f1').attr('stop-opacity', 0.6);
    gradient.append('stop').attr('offset', '100%').attr('stop-color', '#8b5cf6').attr('stop-opacity', 0.6);

    // Draw links
    const link = g.append('g')
        .attr('class', 'links')
        .selectAll('line')
        .data(edges)
        .join('line')
        .attr('class', 'link')
        .attr('stroke', 'url(#linkGradient)')
        .attr('stroke-width', d => Math.max(1, d.weight * 4))
        .attr('stroke-opacity', d => 0.3 + d.weight * 0.5);

    // Draw nodes
    const node = g.append('g')
        .attr('class', 'nodes')
        .selectAll('g')
        .data(nodes)
        .join('g')
        .attr('class', 'node')
        .call(d3.drag()
            .on('start', dragstarted)
            .on('drag', dragged)
            .on('end', dragended));

    // Node circles
    node.append('circle')
        .attr('r', isExplore ? 20 : 16)
        .attr('fill', d => colorScale(d.category || 'Diğer'))
        .attr('stroke', '#fff')
        .attr('stroke-width', 2)
        .style('cursor', 'pointer');

    // Node labels
    node.append('text')
        .text(d => truncateText(d.title, 20))
        .attr('x', 0)
        .attr('y', isExplore ? 35 : 28)
        .attr('text-anchor', 'middle')
        .attr('fill', '#a0a0b0')
        .attr('font-size', '10px')
        .attr('pointer-events', 'none');

    // Hover effects
    node.on('mouseover', function (event, d) {
        d3.select(this).select('circle')
            .transition().duration(200)
            .attr('r', isExplore ? 25 : 20)
            .attr('stroke-width', 3);

        // Highlight connected links
        link.transition().duration(200)
            .attr('stroke-opacity', l => (l.source.id === d.id || l.target.id === d.id) ? 1 : 0.1);

        // Show tooltip
        showGraphTooltip(event, d);
    })
        .on('mouseout', function () {
            d3.select(this).select('circle')
                .transition().duration(200)
                .attr('r', isExplore ? 20 : 16)
                .attr('stroke-width', 2);

            link.transition().duration(200)
                .attr('stroke-opacity', d => 0.3 + d.weight * 0.5);

            hideGraphTooltip();
        })
        .on('click', (event, d) => {
            showDocumentModal(d.id);
        });

    // Update positions on tick
    simulation.on('tick', () => {
        link
            .attr('x1', d => d.source.x)
            .attr('y1', d => d.source.y)
            .attr('x2', d => d.target.x)
            .attr('y2', d => d.target.y);

        node.attr('transform', d => `translate(${d.x},${d.y})`);
    });

    // Drag functions
    function dragstarted(event, d) {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
    }

    function dragged(event, d) {
        d.fx = event.x;
        d.fy = event.y;
    }

    function dragended(event, d) {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
    }

    // Add legend if explore view
    if (isExplore && nodes.length > 0) {
        const categories = [...new Set(nodes.map(n => n.category || 'Diğer'))];
        const legend = svg.append('g')
            .attr('class', 'legend')
            .attr('transform', 'translate(20, 20)');

        categories.forEach((cat, i) => {
            const legendItem = legend.append('g')
                .attr('transform', `translate(0, ${i * 24})`);

            legendItem.append('circle')
                .attr('r', 8)
                .attr('fill', colorScale(cat));

            legendItem.append('text')
                .attr('x', 16)
                .attr('y', 4)
                .attr('fill', '#a0a0b0')
                .attr('font-size', '12px')
                .text(cat);
        });
    }
}

function truncateText(text, maxLength) {
    if (!text) return '';
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
}

// Tooltip
let tooltipEl = null;

function showGraphTooltip(event, d) {
    if (!tooltipEl) {
        tooltipEl = document.createElement('div');
        tooltipEl.style.cssText = `
            position: fixed; z-index: 1000; padding: 12px 16px;
            background: rgba(26, 26, 37, 0.95); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; pointer-events: none; max-width: 300px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5); backdrop-filter: blur(8px);
        `;
        document.body.appendChild(tooltipEl);
    }

    tooltipEl.innerHTML = `
        <div style="font-weight: 600; margin-bottom: 6px; color: #fff;">${escapeHtml(d.title)}</div>
        ${d.category ? `<div style="font-size: 0.85rem; color: #a0a0b0;">Kategori: ${escapeHtml(d.category)}</div>` : ''}
        ${d.source_type ? `<div style="font-size: 0.85rem; color: #a0a0b0;">Tip: ${escapeHtml(d.source_type)}</div>` : ''}
        <div style="font-size: 0.8rem; color: #6366f1; margin-top: 8px;">Detay için tıklayın</div>
    `;

    tooltipEl.style.left = (event.pageX + 15) + 'px';
    tooltipEl.style.top = (event.pageY + 15) + 'px';
    tooltipEl.style.display = 'block';
}

function hideGraphTooltip() {
    if (tooltipEl) tooltipEl.style.display = 'none';
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}
