<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform" 
                xmlns:an="http://docs.oasis-open.org/legaldocml/ns/akn/3.0">   
    <xsl:output method="html" encoding="UTF-8" indent="yes" />
    <xsl:strip-space elements="*"/>

    <!-- Root template -->
    <xsl:template match="/an:akomaNtoso">
        <html>
            <head>
                <title><xsl:value-of select=".//an:FRBRWork/an:FRBRname/@value"/></title>
                <!-- Basic styling can be added here or linked via a CSS file -->
                <style>
                    body { font-family: sans-serif; }
                    h1 { font-size: 2em; text-align: center; }
                    img {
                        display: block;
                        margin-left: auto;
                        margin-right: auto;
                        }

                    .part, .chapter, .section, .subsection, .paragraph, .subparagraph { margin-left: 20px; border-left: 1px solid #eee; padding-left: 15px; margin-top: 10px; }
                    .num { font-weight: bold; margin-right: 5px; }
                    heading { font-weight: bold; margin-top: 1em; margin-bottom: 0.5em; }
                    .section > .heading { font-size: 1.2em; }
                    .part > .heading { font-size: 1.5em; text-align: center; }
                    .chapter > .heading { font-size: 1.3em; text-align: center; }
                </style>
            </head>
            <body>
                <h1><xsl:value-of select=".//an:FRBRWork/an:FRBRname/@value"/></h1>
                <xsl:apply-templates select="an:act | an:bill | an:doc"/>
            </body>
        </html>
    </xsl:template>

    <!-- Process main document containers -->
    <xsl:template match="an:act | an:bill | an:doc">
        <xsl:apply-templates select="an:preface | an:preamble | an:body | an:conclusions"/>
    </xsl:template>

    <!-- Process body and other major sections -->
    <xsl:template match="an:body | an:preface | an:preamble | an:conclusions | an:content | an:intro | an:wrapUp">
        <div>
            <xsl:attribute name="class">
                <xsl:value-of select="local-name()"/>
            </xsl:attribute>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Hierarchical containers -->
    <xsl:template match="an:part | an:chapter | an:hcontainer">
        <div>
            <xsl:attribute name="class">
                <xsl:value-of select="local-name()"/>
            </xsl:attribute>
           <xsl:if test="@style">
                <xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Special handling for sections/subsections etc. to put num inside the first paragraph -->
    <xsl:template match="an:section | an:subsection | an:paragraph | an:subparagraph | an:clause | an:subclause | an:article | an:point | an:indent | an:alinea | an:rule | an:subrule | an:proviso | an:list">
        <div>
            <xsl:attribute name="class">
                <xsl:value-of select="local-name()"/>
            </xsl:attribute>
            <xsl:if test="@style">
                <xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates select="an:heading | an:subheading"/>
            <!-- Process the first paragraph specially to include the number -->
            <xsl:apply-templates select="(an:intro/an:p[1] | an:content/an:p[1])" mode="first-p"/>
            <!-- Process remaining content -->
            <xsl:apply-templates select="an:intro/*[not(self::an:p[1])] | an:content/*[not(self::an:p[1])] | *[not(self::an:num or self::an:heading or self::an:subheading or self::an:intro or self::an:content)]"/>
        </div>
    </xsl:template>

    <!-- Headings and Numbers -->
    <xsl:template match="an:num">
        <span class="num">
            <xsl:apply-templates/>
        </span>
    </xsl:template>

    <xsl:template match="an:heading">
        <div class="heading">
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <!-- Template to handle the first paragraph, injecting the number -->
    <xsl:template match="an:p" mode="first-p">
        <p>
            <xsl:if test="@style">
                <xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates select="../../an:num"/>
            <xsl:apply-templates/>
        </p>
    </xsl:template>

    <!-- Block elements -->
    <xsl:template match="an:p">
        <p>
            <xsl:if test="@style">
                <xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </p>
    </xsl:template>

    <xsl:template match="an:ul">
        <ul><xsl:apply-templates/></ul>
    </xsl:template>

    <xsl:template match="an:ol">
        <ol><xsl:apply-templates/></ol>
    </xsl:template>

    <xsl:template match="an:li">
        <li><xsl:apply-templates/></li>
    </xsl:template>

    <xsl:template match="an:table">
        <table>
            <xsl:if test="@style">
                <xsl:attribute name="style"><xsl:value-of select="@style"/></xsl:attribute>
            </xsl:if>
            <xsl:apply-templates/>
        </table>
    </xsl:template>

    <xsl:template match="an:tr|an:td|an:th|an:caption">
        <xsl:copy><xsl:apply-templates/></xsl:copy>
    </xsl:template>

    <!-- Inline elements -->
    <xsl:template match="an:b">
        <b><xsl:apply-templates/></b>
    </xsl:template>

    <xsl:template match="an:i">
        <i><xsl:apply-templates/></i>
    </xsl:template>

    <xsl:template match="an:ref">
        <a href="{@href}"><xsl:apply-templates/></a>
    </xsl:template>

    <!-- Identity template to copy text and process children of unhandled elements -->
    <xsl:template match="node()|@*">
        <xsl:copy>
            <xsl:apply-templates select="node()|@*"/>
        </xsl:copy>
    </xsl:template>

</xsl:stylesheet>
        