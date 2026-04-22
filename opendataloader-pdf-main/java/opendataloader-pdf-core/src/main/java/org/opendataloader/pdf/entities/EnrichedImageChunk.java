/*
 * Copyright 2025-2026 Hancom Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
package org.opendataloader.pdf.entities;

import org.verapdf.wcag.algorithms.entities.content.ImageChunk;
import org.verapdf.wcag.algorithms.entities.geometry.BoundingBox;

/**
 * An ImageChunk enriched with an AI-generated description (alt text).
 *
 * <p>Created when the hybrid backend returns a SemanticPicture whose bounding
 * box overlaps a Java-extracted ImageChunk. The description is matched by
 * bounding-box IoU in HybridDocumentProcessor and propagated to:
 * <ul>
 *   <li>AutoTaggingProcessor — inserts /Alt into the Figure struct element</li>
 *   <li>ImageSerializer — writes "alt" field to JSON output</li>
 *   <li>MarkdownGenerator / HtmlGenerator — uses description as alt text</li>
 * </ul>
 */
public class EnrichedImageChunk extends ImageChunk {

    private final String description;
    private final BoundingBox extractionBbox;

    /**
     * Creates an EnrichedImageChunk with a custom extraction bounding box.
     *
     * <p>This constructor should be used when matching with a backend SemanticPicture,
     * because the Java ImageChunk's bbox may be filtered/tiny while the SemanticPicture's
     * bbox is the correct size for actual image extraction.
     *
     * @param source The source Java ImageChunk (provides index and StreamInfo).
     * @param extractionBbox The bounding box to use for image extraction (typically SemanticPicture's bbox).
     * @param description The AI-generated description (alt text).
     */
    public EnrichedImageChunk(ImageChunk source, BoundingBox extractionBbox, String description) {
        super(extractionBbox);
        // Copy index so serializers can reference the image file
        setIndex(source.getIndex());
        // Copy stream infos so MCID / struct-tree linkage is preserved
        getStreamInfos().addAll(source.getStreamInfos());
        this.description = description;
        this.extractionBbox = extractionBbox;
    }

    /**
     * Creates an EnrichedImageChunk using the source's bounding box.
     *
     * @param source The source Java ImageChunk.
     * @param description The AI-generated description (alt text).
     * @deprecated Use {@link #EnrichedImageChunk(ImageChunk, BoundingBox, String)} instead
     *             to ensure the correct extraction bbox is used.
     */
    @Deprecated
    public EnrichedImageChunk(ImageChunk source, String description) {
        this(source, source.getBoundingBox(), description);
    }

    @Override
    public BoundingBox getBoundingBox() {
        // Return the extraction bbox, not the source ImageChunk's (which may be tiny/filtered)
        return extractionBbox != null ? extractionBbox : super.getBoundingBox();
    }

    public String getDescription() {
        return description != null ? description : "";
    }

    public boolean hasDescription() {
        return description != null && !description.isEmpty();
    }

    /**
     * Sanitized description safe for use as PDF /Alt, Markdown alt text,
     * HTML alt attribute, and JSON value.
     */
    public String sanitizeDescription() {
        if (!hasDescription()) return "";
        return description
                .replace("\r\n", " ")
                .replace("\n", " ")
                .replace("\r", " ")
                .replace("\"", "")
                .replace("[", "")
                .replace("]", "")
                .replace("<", "")
                .replace(">", "")
                .replace("&", "")
                .replace("\u0000", "")
                .replaceAll("\\s{2,}", " ")
                .trim();
    }
}
